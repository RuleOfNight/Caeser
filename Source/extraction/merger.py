import json
from datetime import datetime
from pathlib import Path
from typing import List

from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file_with_source
from .extractor import extract
from .resolver import ImportResolver
from .models import GraphEdge, GraphNode


def merge_project(project_root: str, output_path: str, project_name: str = None) -> dict:
    """
    Pipeline chính:
      1. Scan tất cả .py (bỏ __init__.py)
      2. Extract từng file → (nodes, edges) với ghost IDs
      3. Dedup nodes theo ID (tránh trùng khi nhiều file khai báo cùng tên)
      4. Resolve ghost IDs → confidence thật
      5. Ghi JSON ra disk
    """
    root = Path(project_root).resolve()
    project_name = project_name or root.name

    # Bỏ __init__.py: re-export của chúng sẽ gây duplicate Module node
    # (xử lý __init__.py flattening là việc của phase sau)
    files = [f for f in scan_py_files(str(root)) if Path(f).name != "__init__.py"]

    all_nodes: List[GraphNode] = []
    all_edges: List[GraphEdge] = []

    print(f"[*] Extracting {len(files)} files...")
    for file_path in files:
        try:
            tree, source = parse_file_with_source(file_path)
            nodes, edges = extract(tree, file_path, source)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        except (SyntaxError, Exception) as e:
            print(f"[-] Skipping {file_path}: {e}")

    # Dedup: giữ lần xuất hiện đầu tiên của mỗi node ID
    seen: set = set()
    deduped: List[GraphNode] = []
    for node in all_nodes:
        if node.id not in seen:
            deduped.append(node)
            seen.add(node.id)

    print(f"[*] Resolving cross-file references...")
    # Resolver cần toàn bộ node list để build lookup map trước khi resolve edges
    resolver = ImportResolver(str(root), deduped)
    resolved_edges = resolver.resolve(all_edges)

    graph = {
        "project": project_name,
        "project_root": str(root),
        "extracted_at": datetime.now().isoformat(),
        "file_count": len(files),
        "nodes": [_node_dict(n) for n in deduped],
        "edges": [_edge_dict(e) for e in resolved_edges],
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    resolved_count = sum(1 for e in resolved_edges if e.confidence > 0.0)
    print(f"[+] Written to {output_path}")
    print(f"    Nodes: {len(deduped)} | Edges: {len(resolved_edges)} ({resolved_count} resolved)")

    return graph


def _node_dict(n: GraphNode) -> dict:
    return {
        "id": n.id,
        "name": n.name,
        "type": n.type.value,
        "file_path": n.file_path,
        "line_start": n.line_start,
        "docstring": n.docstring,
        "source_code": n.source_code,
        "is_async": n.is_async,
        "decorators": n.decorators,
    }


def _edge_dict(e: GraphEdge) -> dict:
    return {
        "type": e.type.value,
        "source_id": e.source_id,
        "target_id": e.target_id,
        "confidence": e.confidence,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--name")
    args = parser.parse_args()
    merge_project(args.input, args.output, args.name)
