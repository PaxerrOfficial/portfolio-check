import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from portfolio_check import check_manifest, main, sha256


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "source.txt").write_bytes(b"original")
        (self.root / "export.txt").write_bytes(b"derivative")
        self.manifest = {"project": "Fictional demo", "source": {
            "file": "source.txt", "sha256": sha256(self.root / "source.txt")},
            "exports": [{"file": "export.txt", "sha256": sha256(self.root / "export.txt"),
                         "width": 1920, "height": 1080, "reviewed": True}]}

    def issues(self):
        return check_manifest(self.manifest, self.root)

    def test_valid_manifest_is_read_only(self):
        before = copy.deepcopy(self.manifest)
        self.assertEqual(self.issues(), [])
        self.assertEqual(self.manifest, before)
        self.assertEqual((self.root / "source.txt").read_bytes(), b"original")
        self.assertEqual((self.root / "export.txt").read_bytes(), b"derivative")

    def test_hash_drift(self):
        (self.root / "export.txt").write_bytes(b"changed after review")
        self.assertTrue(any("differs" in issue for issue in self.issues()))

    def test_original_cannot_be_reused_as_export(self):
        self.manifest["exports"][0].update(self.manifest["source"])
        self.assertTrue(any("distinct" in issue for issue in self.issues()))

    def test_duplicate_exports(self):
        self.manifest["exports"].append(copy.deepcopy(self.manifest["exports"][0]))
        self.assertTrue(any("distinct" in issue for issue in self.issues()))

    def test_escape_paths(self):
        for path in ("../outside.txt", "/tmp/file", "C:/file", "C:file", "dir\\file"):
            with self.subTest(path=path):
                self.manifest["source"]["file"] = path
                self.assertTrue(self.issues())

    def test_external_symlink(self):
        with tempfile.TemporaryDirectory() as other:
            target = Path(other) / "outside.txt"
            target.write_bytes(b"outside")
            try:
                (self.root / "link").symlink_to(target)
            except OSError:
                self.skipTest("Host does not permit symlinks")
            self.manifest["source"]["file"] = "link"
            self.assertTrue(any("inside" in issue for issue in self.issues()))

    def test_missing_and_empty_files(self):
        (self.root / "export.txt").unlink()
        self.assertTrue(any("does not exist" in issue for issue in self.issues()))
        (self.root / "export.txt").touch()
        self.assertTrue(any("empty" in issue for issue in self.issues()))

    def test_review_must_be_boolean_true(self):
        for value in (False, "true", 1, None):
            self.manifest["exports"][0]["reviewed"] = value
            self.assertTrue(any("visual review" in issue for issue in self.issues()))

    def test_dimensions(self):
        for value in (0, -1, True, "1920", 1.5):
            self.manifest["exports"][0]["width"] = value
            self.assertTrue(any("width" in issue for issue in self.issues()))

    def test_bad_shapes(self):
        for value in (None, [], {}, {"project": 4, "source": [], "exports": [None]}):
            self.assertTrue(check_manifest(value, self.root))

    def test_invalid_hash(self):
        self.manifest["source"]["sha256"] = ""
        self.assertTrue(any("64-character" in issue for issue in self.issues()))

    def test_cli_json_and_exit_codes(self):
        path = self.root / "manifest.json"
        for reviewed, status in ((True, 0), (False, 1)):
            self.manifest["exports"][0]["reviewed"] = reviewed
            path.write_text(json.dumps(self.manifest), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["check", str(path), "--json"]), status)
            self.assertEqual(json.loads(output.getvalue())["ok"], reviewed)
        path.write_text("not json", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check", str(path), "--json"]), 2)


if __name__ == "__main__":
    unittest.main()
