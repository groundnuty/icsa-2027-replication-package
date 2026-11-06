"""The first line of every table a snapshot writes: `# snapshot final=<true|false> t=<t>`, so a table cannot be read without knowing which snapshot it
comes from and whether it is the paper's (amendment 29(c)).

Done after `run_all` returns, on the finished files under `--out/tables`, so the analysis writes exactly what it writes outside a snapshot.
A CSV is read with `pd.read_csv(path, skiprows=1)`. Not `comment='#'`: that cuts an unquoted cell at its first #. A Markdown table carries the line
as a heading and a blank line. `manifest.json` and the figures (.png) are not tables and carry no line (SNAPSHOT.json has `final`); any other file
type in the directory is an error, so a table in a new format cannot go unmarked."""
from __future__ import annotations

from pathlib import Path

HEADER_START = "# snapshot "
TABLE_SUFFIXES = (".csv", ".md")


class StampError(RuntimeError):
    pass


def header(final: bool, t: str) -> str:
    return f"{HEADER_START}final={'true' if final else 'false'} t={t}"


def _tables(tdir: Path) -> list[Path]:
    found = []
    for p in sorted(Path(tdir).rglob("*")):
        if not p.is_file():
            continue
        if p.suffix in TABLE_SUFFIXES:
            found.append(p)
        elif p.name != "manifest.json" and p.suffix != ".png":
            raise StampError(f"{p}: neither a table (.csv, .md) nor a known non-table (manifest.json, .png): the header cannot be checked on it")
    return found


def stamp_tables(tdir: Path, line: str) -> int:
    """Puts `line` first in every table under `tdir` (a Markdown table gets a blank line after it). A table that already starts with a snapshot header is an
    error: a stale stamp must not stand for this one. Nothing is written until every file has passed."""
    tables = _tables(tdir)
    data = {p: p.read_bytes() for p in tables}
    for p, b in data.items():
        if b.startswith(HEADER_START.encode()):
            raise StampError(f"{p}: already starts with a snapshot header")
    for p, b in data.items():
        p.write_bytes(line.encode() + (b"\n\n" if p.suffix == ".md" else b"\n") + b)
    return len(tables)


def check_tables(tdir: Path, line: str) -> int:
    """Every table under `tdir` starts with exactly `line`, and there is at least one. Reads the files again, so it checks what is on disk."""
    tables = _tables(tdir)
    if not tables:
        raise StampError(f"no table under {tdir}")
    want = line.encode() + b"\n"
    for p in tables:
        with open(p, "rb") as fh:
            if fh.readline() != want:
                raise StampError(f"{p}: the first line is not the snapshot header {line!r}")
    return len(tables)
