from dataclasses import dataclass, field
from typing import List


# calls lưu tên thô từ AST (vd: "bar", "os.path.join") — chưa resolve thành node_id
@dataclass
class Function:
    name: str
    file: str
    calls: List[str] = field(default_factory=list)


# name = đường dẫn file, dùng làm prefix cho node_id: "file.py::func_name"
@dataclass
class FileModule:
    name: str
    functions: List[Function] = field(default_factory=list)
