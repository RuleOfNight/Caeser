from pathlib import Path
from typing import Dict, List, Optional

from .models import EdgeType, GraphEdge, GraphNode, NodeType


class ImportResolver:
    """
    Nhận danh sách nodes + edges thô (chứa ghost IDs), trả về edges đã resolve.

    Ghost ID scheme (từ extractor):
      dep:module.name     → cần map về module:path
      class_ref:ClassName → cần map về class:path::Name
      func_ref:func_name  → cần map về func:path::Name (best-effort)

    Edges không resolve được (external lib, builtin) giữ confidence=0.0
    và sẽ bị lọc ra ở export/query layer.
    """

    def __init__(self, project_root: str, nodes: List[GraphNode]):
        self._root = Path(project_root).resolve()
        # Ba map riêng vì mỗi loại ghost ID có chiến lược resolve khác nhau
        self._module_map: Dict[str, str] = {}   # "extraction.extractor" → node_id
        self._class_map: Dict[str, List[str]] = {}  # "ClassName" → [node_ids]
        self._func_map: Dict[str, List[str]] = {}   # "func_name" → [node_ids]
        self._build_maps(nodes)

    def _build_maps(self, nodes: List[GraphNode]):
        for node in nodes:
            if node.type == NodeType.MODULE:
                dotted = self._to_dotted(node.file_path)
                if dotted:
                    self._module_map[dotted] = node.id
            elif node.type == NodeType.CLASS:
                self._class_map.setdefault(node.name, []).append(node.id)
            elif node.type == NodeType.FUNCTION:
                self._func_map.setdefault(node.name, []).append(node.id)

    def _to_dotted(self, file_path: str) -> Optional[str]:
        # "C:/project/extraction/extractor.py" → "extraction.extractor"
        try:
            rel = Path(file_path).resolve().relative_to(self._root)
            return rel.with_suffix("").as_posix().replace("/", ".")
        except ValueError:
            return None  # file nằm ngoài project root — bỏ qua

    def resolve(self, edges: List[GraphEdge]) -> List[GraphEdge]:
        return [self._resolve_one(e) for e in edges]

    def _resolve_one(self, edge: GraphEdge) -> GraphEdge:
        tgt = edge.target_id

        if tgt.startswith("dep:"):
            resolved = self._resolve_module(tgt[4:])
            return self._make(edge, resolved, conf_hit=1.0)

        if tgt.startswith("module:"):
            resolved = self._resolve_module(tgt[7:])
            return self._make(edge, resolved, conf_hit=1.0)

        if tgt.startswith("class_ref:"):
            resolved = self._resolve_class(tgt[10:])
            return self._make(edge, resolved, conf_hit=1.0)

        if tgt.startswith("class::"):
            resolved = self._resolve_class(tgt[7:])
            return self._make(edge, resolved, conf_hit=1.0)

        if tgt.startswith("func_ref:"):
            resolved_name = tgt[9:]
            resolved, conf = self._resolve_func(resolved_name, edge.source_id)
            return self._make(edge, resolved, conf_hit=conf)

        if tgt.startswith("func::"):
            resolved_name = tgt[6:]
            resolved, conf = self._resolve_func(resolved_name, edge.source_id)
            return self._make(edge, resolved, conf_hit=conf)

        return edge  # edge đã resolve sẵn (DEFINES, CONTAINS) — giữ nguyên

    def _make(self, edge: GraphEdge, resolved: Optional[str], conf_hit: float) -> GraphEdge:
        if resolved:
            return GraphEdge(
                type=edge.type,
                source_id=edge.source_id,
                target_id=resolved,
                confidence=conf_hit,
            )
        # Không tìm thấy → giữ ghost ID, đánh confidence=0.0 để filter ra sau
        return GraphEdge(
            type=edge.type,
            source_id=edge.source_id,
            target_id=edge.target_id,
            confidence=0.0,
        )

    def _resolve_module(self, module_name: str) -> Optional[str]:
        if module_name in self._module_map:
            return self._module_map[module_name]
        # "from extraction.extractor import X" → module_name = "extraction.extractor"
        # cũng khớp nếu chỉ import package cha "from extraction import ..."
        for key, val in self._module_map.items():
            if key == module_name or key.startswith(module_name + "."):
                return val
        return None  # thư viện ngoài (ast, os, typing…) — drop

    def _resolve_class(self, class_name: str) -> Optional[str]:
        # Dùng phần cuối: "ast.NodeVisitor" → "NodeVisitor" để bỏ qua tiền tố module
        short = class_name.split(".")[-1]
        candidates = self._class_map.get(short, [])
        return candidates[0] if candidates else None

    def _resolve_func(self, func_ref: str, caller_id: str) -> tuple[Optional[str], float]:
        short = func_ref.split(".")[-1]
        candidates = self._func_map.get(short, [])
        if not candidates:
            return None, 0.0
        if len(candidates) == 1:
            # Chỉ một hàm có tên này trong project → khá chắc
            return candidates[0], 0.7
        # Nhiều hàm cùng tên → ưu tiên file giống caller để giảm false positive
        caller_file = caller_id.split("::")[0]
        for prefix in ("func:", "module:", "class:"):
            caller_file = caller_file.replace(prefix, "")
        same_file = [c for c in candidates if caller_file in c]
        return (same_file[0] if same_file else candidates[0]), 0.5
