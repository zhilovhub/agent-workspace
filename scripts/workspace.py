#!/usr/bin/env python3
"""Create task context from templates; no version-control operations."""
import argparse
from datetime import date
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ("AGENTS.md", "BRIEF.md", "STATE.md", "DECISIONS.md")


def new_task(slug, title=None):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Имя задачи: латинские строчные буквы, цифры и дефисы.")
    project = ROOT / "projects" / slug
    for path in (ROOT / "projects", project):
        if path.is_symlink():
            raise ValueError(f"Папка не должна быть символической ссылкой: {path}")
    contents = {
        name: (ROOT / "templates" / "task" / name).read_text(encoding="utf-8")
        .replace("{{TITLE}}", title or slug)
        .replace("{{DATE}}", date.today().isoformat())
        for name in CONTEXT
    }
    project.parent.mkdir(exist_ok=True)
    project.mkdir()
    for name, content in contents.items():
        (project / name).write_text(content, encoding="utf-8")
    (project / "artifacts").mkdir()
    return project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="Создать задачу из шаблона")
    new.add_argument("task")
    new.add_argument("--title")
    args = parser.parse_args()
    try:
        print(new_task(args.task, args.title))
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
