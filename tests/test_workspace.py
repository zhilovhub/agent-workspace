"""Task initialization and user-skill installation in temporary directories."""
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
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / "bundle"
        for folder in ("scripts", "templates", ".agents"):
            shutil.copytree(SOURCE / folder, self.bundle / folder)
        self.project = self.root / "unrelated directory" / "kitchen"
        self.project.mkdir(parents=True)

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(self.bundle / "scripts/workspace.py"), *args],
            cwd=self.project, capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout

    def test_current_directory_is_destination_and_context_is_portable(self):
        self.cli("init", "--title", "Ремонт кухни")
        self.assertIn("Ремонт кухни", (self.project / "BRIEF.md").read_text())
        self.assertTrue((self.project / "artifacts").is_dir())
        self.assertEqual({p.name for p in self.project.iterdir()}, {
            "AGENTS.md", "BRIEF.md", "STATE.md", "DECISIONS.md", "SKILLS.md", "artifacts"
        })
        self.assertFalse((self.bundle / "projects").exists())
        self.assertNotIn("{{DATE}}", (self.project / "STATE.md").read_text())
        rules = (self.project / "AGENTS.md").read_text()
        self.assertNotIn("../../", rules)
        self.assertNotIn(str(self.bundle), rules)

    def test_explicit_directory_preserves_unrelated_files(self):
        target = self.root / "chosen path"
        target.mkdir()
        (target / "notes.txt").write_text("User notes")
        (target / "artifacts").mkdir()
        (target / "artifacts/result.txt").write_text("Result")
        self.cli("init", str(target))
        self.assertEqual((target / "notes.txt").read_text(), "User notes")
        self.assertEqual((target / "artifacts/result.txt").read_text(), "Result")
        self.assertTrue((target / "BRIEF.md").exists())
        self.assertEqual(list(self.project.iterdir()), [])

    def test_any_context_conflict_prevents_all_writes(self):
        (self.project / "STATE.md").write_text("User notes")
        self.cli("init", ok=False)
        self.assertEqual((self.project / "STATE.md").read_text(), "User notes")
        self.assertEqual({p.name for p in self.project.iterdir()}, {"STATE.md"})

    def test_refuses_artifacts_symlink_and_file(self):
        artifacts = self.project / "artifacts"
        artifacts.symlink_to(self.root, target_is_directory=True)
        self.cli("init", ok=False)
        self.assertFalse((self.project / "AGENTS.md").exists())
        artifacts.unlink()
        artifacts.write_text("Existing file")
        self.cli("init", ok=False)
        self.assertEqual(artifacts.read_text(), "Existing file")

    def test_missing_template_prevents_partial_initialization(self):
        (self.bundle / "templates/task/DECISIONS.md").unlink()
        self.cli("init", ok=False)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_install_links_are_idempotent_and_source_can_be_resolved(self):
        destination = self.root / "user-skills"
        self.cli("install", "--skills-dir", str(destination))
        self.cli("install", "--skills-dir", str(destination))
        for name in ("task-start", "context-sync", "context-handoff"):
            link = destination / name
            self.assertTrue(link.is_symlink())
            source = self.bundle / ".agents/skills" / name
            self.assertEqual(link.resolve(), source)
            self.assertEqual((link / "SKILL.md").resolve().parent.parents[2], self.bundle)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_install_preserves_existing_skills_before_any_write(self):
        destination = self.root / "user-skills"
        existing = destination / "context-handoff"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("User skill")
        self.cli("install", "--skills-dir", str(destination), ok=False)
        self.assertEqual((existing / "SKILL.md").read_text(), "User skill")
        self.assertEqual({p.name for p in destination.iterdir()}, {"context-handoff"})

    def test_install_preserves_broken_links(self):
        destination = self.root / "user-skills"
        destination.mkdir()
        link = destination / "context-sync"
        link.symlink_to(self.root / "missing")
        self.cli("install", "--skills-dir", str(destination), ok=False)
        self.assertTrue(link.is_symlink())
        self.assertEqual({p.name for p in destination.iterdir()}, {"context-sync"})


if __name__ == "__main__":
    unittest.main()
