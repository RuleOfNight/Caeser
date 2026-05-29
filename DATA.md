## 📊 Dữ Liệu Struct

### **GraphNode**
```python
from extraction.models import GraphNode, NodeType

node = GraphNode(
    id="app/main.py::run",              # Unique ID
    name="run",                         # Function name
    type=NodeType.FUNCTION,             # Node type
    file_path="app/main.py",            # Source file
    content="Function docstring",       # Description
    source_code="def run(...):\n...",   # Code
    summary="Runs pipeline",            # 1-2 line summary
)
```

### **GraphEdge**
```python
from extraction.models import GraphEdge, EdgeType

edge = GraphEdge(
    source_id="app/main.py::run",
    target_id="ingestion/file_scanner.py::scan_py_files",
    type=EdgeType.CALLS,                # Relationship type
)
```