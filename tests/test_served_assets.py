from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_reader_tools import check_static_copies


class ServedAssetTests(unittest.TestCase):
    def test_stale_empty_and_missing_search_module_fail_before_rebuild(self):
        with tempfile.TemporaryDirectory() as folder:
            source, served = (Path(folder) / name for name in ("source", "served"))
            source.mkdir()
            served.mkdir()
            module = served / "corpus-search.mjs"
            (source / module.name).write_bytes(b"export default 1")
            for data in (None, b"", b"export default 0"):
                with self.subTest(contents=data):
                    if data is not None:
                        module.write_bytes(data)
                    with self.assertRaisesRegex(ValueError, "corpus-search.mjs"):
                        check_static_copies(source, served)
            module.write_bytes(b"export default 1")
            (served / "facsimile.webp").write_bytes(b"tracked publication-only image")
            check_static_copies(source, served)
