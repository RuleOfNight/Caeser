from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# str mixin giúp node.type.value == "Module" khi serialize sang JSON
class NodeType(str, Enum):
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"


class EdgeType(str, Enum):
    IMPORTS = "IMPORTS"   # Module → Module
    DEFINES = "DEFINES"   # Module → Class | top-level Function
    CONTAINS = "CONTAINS" # Class → Method
    CALLS = "CALLS"       # Function → Function (best-effort)
    INHERITS = "INHERITS" # Class → Class


@dataclass
class GraphNode:
    id: str           # scheme: "module:path", "class:path::Name", "func:path::Class::name"
    name: str
    type: NodeType
    file_path: str
    line_start: int
    docstring: Optional[str] = None
    source_code: Optional[str] = None
    is_async: bool = False
    decorators: List[str] = field(default_factory=list)


@dataclass
class GraphEdge:
    type: EdgeType
    source_id: str
    target_id: str
    # 0.0 = unresolved (external lib or ambiguous call) — filtered out in export/query
    confidence: float = 1.0
