"""Test task creation in temporary directories."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("scripts", "templates"):
            shutil.copytree(SOURCE / folder, self.root / folder)

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/workspace.py"), *args],
            cwd=self.temp.name, capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout

    def test_new_creates_context_and_artifacts(self):
        self.cli("new", "sample", "--title", "Ремонт кухни")
        task = self.root / "projects/sample"
        self.assertIn("Ремонт кухни", (task / "BRIEF.md").read_text())
        self.assertTrue((task / "artifacts").is_dir())
        self.assertEqual({p.name for p in task.iterdir()}, {
            "AGENTS.md", "BRIEF.md", "STATE.md", "DECISIONS.md", "artifacts"
        })
        self.assertNotIn("{{DATE}}", (task / "STATE.md").read_text())

    def test_refuses_overwrite(self):
        self.cli("new", "sample")
        state = self.root / "projects/sample/STATE.md"
        state.write_text("User notes")
        self.cli("new", "sample", ok=False)
        self.assertEqual(state.read_text(), "User notes")

    def test_refuses_path_escape(self):
        self.cli("new", "../escape", ok=False)
        self.assertFalse((self.root / "escape").exists())
        self.assertFalse((self.root / "projects").exists())

    def test_refuses_symlinked_projects(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "projects").symlink_to(outside, target_is_directory=True)
        self.cli("new", "sample", ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_missing_template_does_not_leave_partial_task(self):
        (self.root / "templates/task/DECISIONS.md").unlink()
        self.cli("new", "sample", ok=False)
        self.assertFalse((self.root / "projects/sample").exists())


if __name__ == "__main__":
    unittest.main()
