#!/usr/bin/env python3
"""Initialize task context anywhere or install user skills; no VCS operations."""
import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ("AGENTS.md", "BRIEF.md", "STATE.md", "DECISIONS.md", "SKILLS.md")
SKILLS = ("task-start", "context-sync", "context-handoff")


def init_task(directory=".", title=None):
    project = Path(directory).expanduser().absolute()
    if project.is_symlink():
        raise ValueError(f"Директория задачи — символическая ссылка: {project}")
    if project.exists() and not project.is_dir():
        raise ValueError(f"Ожидается директория: {project}")
    contents = {
        name: (ROOT / "templates" / "task" / name).read_text(encoding="utf-8")
        .replace("{{TITLE}}", title or project.name)
        .replace("{{DATE}}", date.today().isoformat())
        for name in CONTEXT
    }
    conflicts = [name for name in CONTEXT
                 if (project / name).exists() or (project / name).is_symlink()]
    artifacts = project / "artifacts"
    if artifacts.is_symlink() or (artifacts.exists() and not artifacts.is_dir()):
        conflicts.append("artifacts")
    if conflicts:
        raise ValueError("Файлы сохранены; инициализация отменена. Уже существуют: "
                         + ", ".join(conflicts))
    project.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a file appearing after preflight.
    for name, content in contents.items():
        with (project / name).open("x", encoding="utf-8") as stream:
            stream.write(content)
    artifacts.mkdir(exist_ok=True)
    return project.resolve()


def install_skills(directory=None):
    destination = Path(directory).expanduser().absolute() if directory else (
        Path.home() / ".agents" / "skills"
    )
    links = []
    for name in SKILLS:
        source = ROOT / ".agents" / "skills" / name
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Нет инструкции скилла: {source}")
        target = destination / name
        if target.is_symlink() and target.resolve() == source.resolve():
            continue
        if target.exists() or target.is_symlink():
            raise ValueError(f"Установка отменена: существующий скилл сохранён: {target}")
        links.append((source, target))
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in links:
        target.symlink_to(source, target_is_directory=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", aliases=["new"],
                               help="Создать контекст в текущей или указанной директории")
    init.add_argument("directory", nargs="?", default=".")
    init.add_argument("--title")
    install = commands.add_parser("install", help="Установить три пользовательских скилла")
    install.add_argument("--skills-dir", help="Вместо ~/.agents/skills")
    args = parser.parse_args()
    try:
        if args.command == "install":
            print(install_skills(args.skills_dir))
        else:
            print(init_task(args.directory, args.title))
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
