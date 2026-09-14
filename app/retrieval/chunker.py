import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

TARGET_WORDS = 180
MAX_WORDS = 260

# ASCII plus Latin-1 Supplement (ordinary accented letters - é, ü, ñ, etc.,
# common in real names and places) plus a small set of typographic
# punctuation already used in this KB. Anything else - the Nama
# click-consonant letter that got a real call rejected with 400 earlier is
# the concrete example - gets replaced with a space rather than silently
# kept, since a phone task string is read aloud by a TTS pipeline that has
# no obligation to accept characters outside common ranges. Applied to
# every chunk regardless of source, not just PDFs, since a future manual
# edit could reintroduce the same mistake.
_SAFE_EXTRA_CHARS = "–—‘’“”…"  # – — ‘ ’ “ ” …


def _sanitize_text(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if code < 0x80 or 0x00A0 <= code <= 0x00FF or ch in _SAFE_EXTRA_CHARS:
            out.append(ch)
        else:
            out.append(" ")
    return re.sub(r"[ \t]+", " ", "".join(out))


@dataclass
class Chunk:
    id: str
    tenant: str
    source: str  # filename
    title: str  # frontmatter title
    topic: str
    office: str
    heading: str  # e.g. "Proof of registration › When it is blocked"
    text: str


def parse_frontmatter(raw: str) -> Tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, fm, body = raw.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def chunk_file(path: Path, tenant: str) -> List[Chunk]:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    title = meta.get("title", path.stem)

    chunks: List[Chunk] = []
    current_heading = title
    buffer: List[str] = []
    n = 0

    def flush():
        nonlocal buffer, n
        if not buffer:
            return
        text = _sanitize_text(" ".join(buffer).strip())
        if text:
            chunks.append(
                Chunk(
                    id=f"{tenant}:{path.stem}:{len(chunks)}",
                    tenant=tenant,
                    source=path.name,
                    title=title,
                    topic=meta.get("topic", path.stem),
                    office=meta.get("office", "registrar"),
                    heading=current_heading,
                    text=text,
                )
            )
        buffer, n = [], 0

    for line in body.splitlines():
        if re.match(r"^#{1,6}\s", line):
            flush()
            current_heading = f"{title} › {line.lstrip('# ').strip()}"
            continue
        words = len(line.split())
        if n + words > MAX_WORDS:
            flush()
        buffer.append(line)
        n += words
        if n >= TARGET_WORDS:
            flush()

    flush()
    return chunks


def chunk_pdf(path: Path, tenant: str) -> List[Chunk]:
    """Same word-count-based chunking as chunk_file(), driven by extracted
    PDF text instead of markdown - no frontmatter exists, so topic/office
    fall back the same way an .md file without frontmatter would. Heading
    is page-based rather than markdown-header-based, since PDFs don't have
    the latter; a chunk spanning a page boundary is labelled with whichever
    page it happened to flush on, not necessarily where it started - close
    enough for provenance display, not worth exact tracking.
    """
    import pdfplumber

    title = path.stem.replace("_", " ").replace("-", " ").strip()
    chunks: List[Chunk] = []
    buffer: List[str] = []
    n = 0
    current_page = 1

    def flush():
        nonlocal buffer, n
        if not buffer:
            return
        text = _sanitize_text(" ".join(buffer).strip())
        if text:
            chunks.append(
                Chunk(
                    id=f"{tenant}:{path.stem}:{len(chunks)}",
                    tenant=tenant,
                    source=path.name,
                    title=title,
                    topic=path.stem,
                    office="registrar",
                    heading=f"{title} › page {current_page}",
                    text=text,
                )
            )
        buffer, n = [], 0

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            current_page = page_num
            for line in (page.extract_text() or "").splitlines():
                words = len(line.split())
                if n + words > MAX_WORDS:
                    flush()
                buffer.append(line)
                n += words
                if n >= TARGET_WORDS:
                    flush()

    flush()
    return chunks
