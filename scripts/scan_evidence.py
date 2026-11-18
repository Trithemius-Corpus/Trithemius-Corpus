"""Validate immutable source images and exact crops for AI scan assessments."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops


def load(root: Path, work_id: str) -> dict:
    path = root / 'data/translation_disagreements' / work_id / 'scan-assessments.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['human_review'] != 'none_documented':
        raise ValueError('AI scan ledger cannot supply undocumented human review')
    for item in data['items'].values():
        if item['reviewer'] != 'Codex AI' or item['human_review'] != 'none_documented':
            raise ValueError('invalid scan-review attribution')
        paths=[]
        for ref,key in ((item['image'],'path'),(item['crop'],'crop_path')):
            target=(root/ref[key]).resolve()
            if not target.is_relative_to(root.resolve()):raise ValueError('image path escaped repository')
            if hashlib.sha256(target.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('scan/crop digest mismatch')
            paths.append(target)
        x,y,w,h=item['crop']['xywh']
        with Image.open(paths[0]) as original, Image.open(paths[1]) as crop:
            if not (0<=x<x+w<=original.width and 0<=y<y+h<=original.height):raise ValueError('crop bounds invalid')
            if crop.size!=(w,h) or ImageChops.difference(original.crop((x,y,x+w,y+h)).convert('RGB'),crop.convert('RGB')).getbbox():
                raise ValueError('crop is not an exact region of the source image')
    return data['items']
