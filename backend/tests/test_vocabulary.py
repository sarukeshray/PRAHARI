"""Guards design rule 1: the system never alleges wrongdoing.

Only source directories are scanned — ``backend/app`` and ``frontend/src``.
Documentation (README, DECISIONS, the build specification) is deliberately out
of scope, because those files must be able to *discuss* the constraint in order
to explain it.  This test file is itself outside the scanned tree.

Kept in the suite from Phase 0 so a violation is caught the commit it appears in,
rather than during a pre-demo audit.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCANNED_TREES = (
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "frontend" / "src",
)

SCANNED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".json", ".css", ".html"}

# Substring match, case-insensitive. "fraud" also catches "fraudulent"/"defraud".
PROHIBITED_TERMS = ("fraud", "corrupt", "guilty", "embezzl", "culprit")

PERMITTED_VOCABULARY = ("risk", "anomaly", "flag", "deviation", "violation")


def _source_files() -> list[Path]:
    files: list[Path] = []
    for tree in SCANNED_TREES:
        if not tree.exists():
            continue
        for path in tree.rglob("*"):
            if path.suffix.lower() not in SCANNED_SUFFIXES:
                continue
            if any(part in {"node_modules", "__pycache__", ".venv", "dist"} for part in path.parts):
                continue
            files.append(path)
    return files


def test_source_trees_are_not_empty() -> None:
    """Fails loudly if the scan silently matches nothing, which would make the
    vocabulary check below vacuously pass."""
    assert _source_files(), f"no source files found under {[str(t) for t in SCANNED_TREES]}"


@pytest.mark.parametrize("term", PROHIBITED_TERMS)
def test_no_accusatory_vocabulary_in_source(term: str) -> None:
    offenders: list[str] = []

    for path in _source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if term in line.lower():
                rel = path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        f"Prohibited term {term!r} found in source. PRAHARI reports risk indicators "
        f"requiring human review, never allegations of wrongdoing. "
        f"Use one of {PERMITTED_VOCABULARY} instead.\n  " + "\n  ".join(offenders)
    )
