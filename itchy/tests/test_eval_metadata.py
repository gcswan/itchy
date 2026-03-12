import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = REPO_ROOT / "scratchiq-workspace" / "iteration-1"
SKILL_EVALS_PATH = REPO_ROOT / "scratchiq" / "evals" / "evals.json"


class EvalMetadataTests(unittest.TestCase):
    def test_top_level_evals_file_references_existing_photo_fixture(self):
        data = json.loads(SKILL_EVALS_PATH.read_text(encoding="utf-8"))
        photo_eval = next(item for item in data["evals"] if item["id"] == 2)
        self.assertIn("fixtures/nc_display_photo.png", photo_eval["files"])
        self.assertTrue((REPO_ROOT / "scratchiq" / "evals" / "fixtures" / "nc_display_photo.png").exists())

    def test_iteration_eval_metadata_has_non_empty_assertions(self):
        metadata_paths = sorted(WORKSPACE_DIR.glob("*/eval_metadata.json"))
        self.assertGreaterEqual(len(metadata_paths), 3)

        for path in metadata_paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("assertions", data, msg=str(path))
            self.assertTrue(data["assertions"], msg=str(path))
            self.assertTrue(all(isinstance(assertion, str) and assertion.strip() for assertion in data["assertions"]), msg=str(path))


if __name__ == "__main__":
    unittest.main()
