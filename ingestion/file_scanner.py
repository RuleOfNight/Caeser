from pathlib import Path

_EXCLUDE = {".venv", "venv", "__pycache__", ".git"}


def scan_py_files(root: str) -> list[str]:
    return [
        p.as_posix()
        for p in Path(root).rglob("*.py")
        if p.is_file() and not _EXCLUDE.intersection(p.parts)
    ]
