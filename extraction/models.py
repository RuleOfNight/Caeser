from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

class NodeType(Enum):
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    VARIABLE = "Variable"
    DEPENDENCY = "Dependency"

class EdgeType(Enum):
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPORTS = "IMPORTS"
    USES_VARIABLE = "USES_VARIABLE"

@dataclass
class GraphNode:
    id: str
    name: str
    type: NodeType
    file_path: str
    content: str = ""        # Lưu docstring hoặc text mô tả
    source_code: str = ""    # LƯU MÃ NGUỒN THÔ CỦA HÀM/CLASS ĐỂ AI ĐỌC
    summary: str = ""        # Bản tóm tắt 1-2 câu do AI sinh ra (để tiết kiệm token)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    type: EdgeType