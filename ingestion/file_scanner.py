from pathlib import Path

_EXCLUDE = {".venv", "venv", "__pycache__", ".git", "tests"}


def scan_py_files(root: str) -> list[str]:
    path = Path(root)
    if path.is_file():
        return [path.as_posix()] if path.suffix == ".py" else []

    return [
        p.as_posix()
        for p in path.rglob("*.py")
        if p.is_file() and not _EXCLUDE.intersection(p.parts)
    ]
