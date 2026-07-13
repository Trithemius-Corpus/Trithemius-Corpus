# /// script
# dependencies = [
#   "unsloth",
#   "trl",
#   "datasets",
#   "transformers",
#   "accelerate",
#   "peft",
#   "bitsandbytes",
#   "pillow",
#   "trackio",
#   "huggingface_hub",
# ]
# ///
"""Train a Qwen3-VL OCR LoRA with Unsloth.

This script is meant for a free-first Colab/Unsloth workflow. Build the dataset
locally with build_qwen3vl_ocr_lora_dataset.py, upload or mount the dataset
directory in Colab, then run a small 500-step smoke pass before any longer run.
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def assistant_text(row: dict[str, Any]) -> str:
    if isinstance(row.get("target"), str):
        return row["target"]
    for message in row.get("messages", []):
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(text for text in texts if text)
    return ""


def normalize_row(row: dict[str, Any], dataset_dir: Path) -> dict[str, Any]:
    from PIL import Image

    normalized = dict(row)
    images = []
    for image_ref in row.get("images", []):
        image_path = Path(image_ref)
        if not image_path.is_absolute():
            image_path = dataset_dir / image_path
        with Image.open(image_path) as image:
            images.append(image.convert("RGB").copy())
    normalized["images"] = images

    target = assistant_text(row)
    messages = row.get("messages") or []
    if not messages:
        raise ValueError(f"Row {row.get('id')} has no messages")
    if not any(message.get("role") == "assistant" for message in messages):
        messages = list(messages) + [
            {"role": "assistant", "content": [{"type": "text", "text": target}]}
        ]
    normalized["messages"] = messages
    return normalized


def load_split(dataset_dir: Path, split: str, limit: int | None = None):
    from datasets import Dataset

    path = dataset_dir / f"{split}.jsonl"
    if not path.exists():
        return None
    rows = read_jsonl(path)
    if limit:
        rows = rows[:limit]
    if not rows:
        return None
    return Dataset.from_list([normalize_row(row, dataset_dir) for row in rows])


def load_unsloth_model(args: argparse.Namespace):
    from unsloth import FastVisionModel

    model, processor = FastVisionModel.from_pretrained(
        model_name=args.model,
        load_in_4bit=not args.no_4bit,
        use_gradient_checkpointing="unsloth" if args.gradient_checkpointing else False,
    )

    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers=not args.freeze_vision,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        random_state=args.seed,
        use_rslora=args.use_rslora,
    )

    try:
        from unsloth.chat_templates import get_chat_template

        processor = get_chat_template(processor, "qwen3-vl")
    except Exception:
        pass

    return model, processor


def resolve_eos_token(processor: Any) -> str | None:
    tokenizer = getattr(processor, "tokenizer", processor)
    bad_tokens = {"<EOS_TOKEN>", ""}
    vocab = None
    try:
        vocab = tokenizer.get_vocab()
    except Exception:
        pass

    def is_valid(candidate: str | None) -> bool:
        if not candidate or candidate in bad_tokens:
            return False
        if vocab is not None:
            return candidate in vocab
        if hasattr(tokenizer, "convert_tokens_to_ids"):
            try:
                token_id = tokenizer.convert_tokens_to_ids(candidate)
                unk_id = getattr(tokenizer, "unk_token_id", None)
                return token_id is not None and token_id != unk_id
            except Exception:
                return False
        return False

    eos_token = getattr(tokenizer, "eos_token", None)
    if is_valid(eos_token):
        return eos_token

    eos_token_id = getattr(tokenizer, "eos_token_id", None)
    if eos_token_id is not None and hasattr(tokenizer, "convert_ids_to_tokens"):
        candidate = tokenizer.convert_ids_to_tokens(eos_token_id)
        if is_valid(candidate):
            return candidate

    for candidate in ("<|im_end|>", "<|endoftext|>"):
        if is_valid(candidate):
            return candidate
    return None


def train(args: argparse.Namespace) -> None:
    if args.dry_run:
        train_count = count_jsonl(args.dataset_dir / "train.jsonl")
        validation_count = count_jsonl(args.dataset_dir / "validation.jsonl")
        print(f"Model: {args.model}")
        print(f"Train examples: {train_count}")
        print(f"Validation examples: {validation_count}")
        print(f"Output: {args.output_dir}")
        print("Dry run only; model was not loaded and training was not started.")
        return

    try:
        import unsloth  # noqa: F401
        from unsloth import FastVisionModel, is_bfloat16_supported
        from unsloth.trainer import UnslothVisionDataCollator
        from trl import SFTConfig, SFTTrainer
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "Training dependencies are not importable. In Colab, install/run the "
            "Unsloth Qwen3-VL notebook environment first, then rerun this script.\n"
            f"Import error: {type(exc).__name__}: {exc}"
        ) from exc

    train_dataset = load_split(args.dataset_dir, "train", args.max_train_examples)
    eval_dataset = load_split(args.dataset_dir, "validation", args.max_eval_examples)
    if train_dataset is None:
        raise SystemExit(f"No train rows found in {args.dataset_dir / 'train.jsonl'}")

    print(f"Model: {args.model}")
    print(f"Train examples: {len(train_dataset)}")
    print(f"Validation examples: {len(eval_dataset) if eval_dataset is not None else 0}")
    print(f"Output: {args.output_dir}")

    model, processor = load_unsloth_model(args)
    FastVisionModel.for_training(model)
    tokenizer_for_trainer = getattr(processor, "tokenizer", processor)

    report_to = "none" if args.no_trackio else "trackio"
    config_kwargs = {
        "per_device_train_batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "warmup_steps": args.warmup_steps,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "fp16": not is_bfloat16_supported(),
        "bf16": is_bfloat16_supported(),
        "logging_steps": args.logging_steps,
        "save_steps": args.save_steps,
        "optim": args.optim,
        "weight_decay": args.weight_decay,
        "lr_scheduler_type": args.lr_scheduler_type,
        "seed": args.seed,
        "output_dir": str(args.output_dir),
        "report_to": report_to,
        "remove_unused_columns": False,
        "dataset_text_field": "",
        "dataset_kwargs": {"skip_prepare_dataset": True},
        "max_length": args.max_seq_length,
    }
    eos_token = resolve_eos_token(processor)
    if "eos_token" in inspect.signature(SFTConfig).parameters:
        config_kwargs["eos_token"] = eos_token
    if eos_token:
        print(f"EOS token: {eos_token}")
    else:
        print("EOS token: None")
    try:
        training_args = SFTConfig(**config_kwargs)
    except TypeError as exc:
        if "eos_token" not in str(exc):
            raise
        config_kwargs.pop("eos_token", None)
        training_args = SFTConfig(**config_kwargs)
    if hasattr(training_args, "eos_token"):
        training_args.eos_token = eos_token
    if eos_token and hasattr(tokenizer_for_trainer, "convert_tokens_to_ids"):
        eos_token_id = tokenizer_for_trainer.convert_tokens_to_ids(eos_token)
        tokenizer_for_trainer.eos_token = eos_token
        tokenizer_for_trainer.eos_token_id = eos_token_id
        if not getattr(tokenizer_for_trainer, "pad_token", None):
            tokenizer_for_trainer.pad_token = eos_token
            tokenizer_for_trainer.pad_token_id = eos_token_id

    trainer_kwargs = {
        "model": model,
        "data_collator": UnslothVisionDataCollator(model, processor),
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "args": training_args,
    }
    trainer_signature = inspect.signature(SFTTrainer.__init__).parameters
    if "processing_class" in trainer_signature:
        trainer_kwargs["processing_class"] = tokenizer_for_trainer
    else:
        trainer_kwargs["tokenizer"] = tokenizer_for_trainer
    trainer = SFTTrainer(**trainer_kwargs)
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    adapter_dir = args.output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir)
    processor.save_pretrained(adapter_dir)
    print(f"Saved LoRA adapter to {adapter_dir}")

    if args.hub_model_id:
        model.push_to_hub(args.hub_model_id, private=args.private_hub)
        processor.push_to_hub(args.hub_model_id, private=args.private_hub)
        print(f"Pushed adapter to https://huggingface.co/{args.hub_model_id}")

    tokenizer = getattr(processor, "tokenizer", processor)
    if args.save_merged:
        merged_dir = args.output_dir / "merged-16bit"
        model.save_pretrained_merged(str(merged_dir), tokenizer, save_method="merged_16bit")
        print(f"Saved merged 16-bit model to {merged_dir}")

    if args.save_gguf:
        gguf_dir = args.output_dir / f"gguf-{args.gguf_quantization}"
        model.save_pretrained_gguf(
            str(gguf_dir),
            tokenizer,
            quantization_method=args.gguf_quantization,
        )
        print(f"Saved GGUF export to {gguf_dir}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / ".cache" / "qwen3vl-ocr-lora-dataset" / "v0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".cache" / "qwen3vl-ocr-lora-runs" / "qwen3vl-4b-ocr-lora-v0")
    parser.add_argument("--model", default="unsloth/Qwen3-VL-4B-Instruct")
    parser.add_argument("--fallback-model", default="unsloth/Qwen3-VL-2B-Instruct")
    parser.add_argument("--freeze-vision", action="store_true", help="OOM mitigation before falling back to 2B.")
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--warmup-steps", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.0)
    parser.add_argument("--use-rslora", action="store_true")
    parser.add_argument("--max-seq-length", type=int)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--optim", default="adamw_8bit")
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lr-scheduler-type", default="linear")
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--resume-from-checkpoint", action="store_true")
    parser.add_argument("--max-train-examples", type=int)
    parser.add_argument("--max-eval-examples", type=int)
    parser.add_argument("--no-trackio", action="store_true")
    parser.add_argument("--hub-model-id")
    parser.add_argument("--private-hub", action="store_true")
    parser.add_argument("--save-merged", action="store_true")
    parser.add_argument("--save-gguf", action="store_true")
    parser.add_argument("--gguf-quantization", default="q4_k_m")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        train(args)
    except RuntimeError as exc:
        message = str(exc).lower()
        if "out of memory" in message or "cuda oom" in message:
            print(
                "CUDA OOM detected. First retry with --freeze-vision and a 512 px "
                "dataset. If that still fails, rerun with "
                f"--model {args.fallback_model}.",
                file=sys.stderr,
            )
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
