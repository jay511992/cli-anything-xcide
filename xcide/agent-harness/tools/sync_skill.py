"""Copy the repository skill and its published references into the Python package."""

import argparse
import json
from pathlib import Path


def published_files(skill: Path):
    suite = Path("references/xc-suite")
    manifest = suite / "SOURCE.json"
    yield Path("SKILL.md")
    yield Path("SKILL.html")
    yield manifest
    for entry in json.loads((skill / manifest).read_text(encoding="utf-8"))["files"]:
        relative = Path(entry["path"])
        if relative.name == "SKILL.md":
            relative = relative.with_name("GUIDE.md")
        yield suite / relative
        if relative.suffix == ".md":
            yield suite / relative.with_suffix(".html")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report missing or outdated package files without writing")
    args = parser.parse_args()
    harness = Path(__file__).resolve().parents[1]
    skill = harness.parents[1] / "skills/cli-anything-xcide"
    destination = harness / "cli_anything/xcide/skills"
    differences = []
    for relative in published_files(skill):
        content = (skill / relative).read_bytes()
        target = destination / relative
        if target.is_file() and target.read_bytes() == content:
            continue
        differences.append(relative.as_posix())
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    if args.check and differences:
        print("Outdated skill files:\n" + "\n".join(differences))
        return 1
    print("Skill copies match." if args.check else f"Updated {len(differences)} package files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
