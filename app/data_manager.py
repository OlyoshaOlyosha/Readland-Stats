"""Read/write the Readlang CSV, preserving all sections except `Your words`."""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from app.config import CSV_PATH
from app.models import WordEntry

WORDS_MARKER = "Your words (csv format)"
FIELDS = list(WordEntry.__dataclass_fields__.keys())


def backup_csv() -> str | None:
    """Copy the current CSV into data/backups/ with a UTC timestamp.

    Returns the backup path, or None if the file doesn't exist.
    """
    if not CSV_PATH.exists():
        return None
    backup_dir = CSV_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"{CSV_PATH.stem}-{stamp}{CSV_PATH.suffix}"
    dest.write_bytes(CSV_PATH.read_bytes())
    return str(dest)


def _read_lines(path: Path) -> list[str]:
    """Read file as list of lines, keeping line endings for byte-faithful writeback."""
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def _find_words_bounds(lines: list[str]) -> tuple[int, int]:
    """Return (header_idx, end_idx) — slice of lines containing the words table."""
    start = next(i for i, line in enumerate(lines) if WORDS_MARKER in line)
    header_idx = start
    while not lines[header_idx].lstrip().startswith('"word"'):
        header_idx += 1
    end_idx = len(lines)
    for i in range(header_idx + 1, len(lines)):
        if "(csv format)" in lines[i]:
            end_idx = i
            break
    return header_idx, end_idx


def load_words() -> list[WordEntry]:
    """Parse the `Your words` section into dataclasses. Ignores blank rows."""
    lines = _read_lines(CSV_PATH)
    header_idx, end_idx = _find_words_bounds(lines)
    reader = csv.DictReader(lines[header_idx:end_idx])
    result: list[WordEntry] = []
    for row in reader:
        if not row.get("word"):
            continue
        clean = {k: (row.get(k) or "") for k in FIELDS}
        result.append(WordEntry(**clean))
    return result


def save_words(words: list[WordEntry]) -> None:
    """Replace the `Your words` section in-place; keep everything else byte-identical."""
    lines = _read_lines(CSV_PATH)
    header_idx, end_idx = _find_words_bounds(lines)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writeheader()
    for w in words:
        writer.writerow({k: getattr(w, k) or "" for k in FIELDS})
    new_section = buf.getvalue().splitlines(keepends=True)
    if not new_section[-1].endswith("\n"):
        new_section[-1] += "\n"

    tail = lines[end_idx:]
    if tail and not tail[0].startswith("\n"):
        new_section.append("\n")

    CSV_PATH.write_text("".join(lines[:header_idx] + new_section + tail), encoding="utf-8")
