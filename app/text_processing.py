import re
from collections.abc import Iterable


SECTION_PATTERN = re.compile(
    r"^(Article\s+\d+[A-Za-z]?|ANNEX\s+[IVXLC]+|CHAPTER\s+[IVXLC]+)\s*$",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"02024R1689\s+[—-]\s+EN\s+[—-].*?\n", "", text)
    return text.strip()


def split_sections(text: str, current_section: str | None = None) -> tuple[list[tuple[str | None, str]], str | None]:
    sections: list[tuple[str | None, str]] = []
    buffer: list[str] = []
    section = current_section

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if SECTION_PATTERN.match(line):
            if buffer:
                block = "\n".join(buffer).strip()
                if block:
                    sections.append((section, block))
                buffer = []
            section = line
        buffer.append(raw_line)

    if buffer:
        block = "\n".join(buffer).strip()
        if block:
            sections.append((section, block))

    return sections, section


def chunk_text(text: str, max_chars: int = 2200, overlap_chars: int = 250) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                chunks.append(paragraph[start:end].strip())
                if end == len(paragraph):
                    break
                start = max(0, end - overlap_chars)
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            overlap = current[-overlap_chars:].strip()
            current = f"{overlap}\n\n{paragraph}".strip() if overlap else paragraph
        else:
            current = paragraph

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if len(chunk) >= 80]


def batched(items: list, size: int) -> Iterable[list]:
    for index in range(0, len(items), size):
        yield items[index : index + size]
