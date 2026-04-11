import os
import pytest
from ingestion.file_scanner import scan_py_files

def test_scan_py_files_returns_only_py_files(tmp_path):
    (tmp_path / "script.py").write_text("print('hello')")
    (tmp_path / "readme.md").write_text("# doc")
    
    sub_dir = tmp_path / "module"
    sub_dir.mkdir()
    (sub_dir / "utils.py").write_text("def noop(): pass")
    
    files = scan_py_files(str(tmp_path))
    
    assert len(files) == 2
    paths = [os.path.basename(f) for f in files]
    assert "script.py" in paths
    assert "utils.py" in paths
    assert "readme.md" not in paths

def test_scan_invalid_directory():
    assert scan_py_files("non_existent_folder") == []
