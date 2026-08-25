from pathlib import Path


def update_readme_section(readme: Path, start_marker: str, end_marker: str, content: str) -> None:
    text = readme.read_text(encoding="utf-8")
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    updated = text[:start] + "\n" + content.strip() + "\n" + text[end:]
    readme.write_text(updated, encoding="utf-8", newline="\n")
