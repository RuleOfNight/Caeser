from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Sequence

import networkx as nx

from extraction.extractor import extract
from extraction.models import EdgeType, FileModule, Function, GraphEdge, GraphNode, NodeType
from extraction.resolver import ImportResolver
from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file_with_source


ENTRY_FILE_NAMES = {
    "__main__.py",
    "app.py",
    "cli.py",
    "main.py",
    "run.py",
    "server.py",
    "ask.py",
}

ENTRY_FUNCTION_NAMES = {
    "main",
    "run",
    "start",
    "serve",
    "cli",
    "launch",
    "bootstrap",
}

VIEWER_DIRS = {"app", "graph", "tests", "memory", "prompts"}

DETAIL_EDGE_TYPES = {
    EdgeType.DEFINES.value,
    EdgeType.CONTAINS.value,
    EdgeType.CALLS.value,
    EdgeType.IMPORTS.value,
    EdgeType.INHERITS.value,
}


def build_graph(items: Sequence[Any], edges: Sequence[GraphEdge] | None = None) -> nx.MultiDiGraph:
    """Build a NetworkX graph from either compatibility modules or extracted nodes.

    The older unit tests still pass [FileModule(...)] into this function.
    The new viewer passes [GraphNode, ...] + [GraphEdge, ...].
    """

    if edges is None and _looks_like_compat_modules(items):
        return _build_compat_graph(items)
    return _build_extracted_graph(items, edges or [])


def build_project_graph(project_root: str) -> nx.MultiDiGraph:
    """Scan, extract, resolve, and build the full project graph in memory."""

    root = Path(project_root).resolve()
    files = [path for path in scan_py_files(str(root)) if Path(path).name != "__init__.py"]

    all_nodes: list[GraphNode] = []
    all_edges: list[GraphEdge] = []
    for file_path in files:
        try:
            tree, source = parse_file_with_source(file_path)
            nodes, edges = extract(tree, file_path, source)
        except (SyntaxError, OSError):
            continue
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    deduped_nodes: list[GraphNode] = []
    seen: set[str] = set()
    for node in all_nodes:
        if node.id in seen:
            continue
        deduped_nodes.append(node)
        seen.add(node.id)

    resolver = ImportResolver(str(root), deduped_nodes)
    resolved_edges = resolver.resolve(all_edges)
    return build_graph(deduped_nodes, resolved_edges)


def build_overview_graph(full_graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Collapse the project into a file-level overview graph."""

    overview = nx.MultiDiGraph()
    file_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"node_count": 0, "function_count": 0, "class_count": 0, "dependency_count": 0}
    )

    for node_id, data in full_graph.nodes(data=True):
        file_path = data.get("file_path")
        if not file_path:
            continue
        stats = file_stats[file_path]
        stats["node_count"] += 1
        node_type = data.get("type")
        if node_type == NodeType.FUNCTION.value:
            stats["function_count"] += 1
        elif node_type == NodeType.CLASS.value:
            stats["class_count"] += 1
        elif node_type == NodeType.MODULE.value:
            stats["dependency_count"] += 1

    for file_path, stats in file_stats.items():
        label = Path(file_path).name
        overview.add_node(
            file_path,
            name=label,
            type="File",
            file_path=file_path,
            stats=stats,
            display_title=f"{label}\n({stats['node_count']} nodes)",
            size=3600 + stats["node_count"] * 150,
        )

    edge_weights: dict[tuple[str, str, str], int] = defaultdict(int)
    for source_id, target_id, edge_data in full_graph.edges(data=True):
        relationship = edge_data.get("relationship")
        if relationship not in {EdgeType.IMPORTS.value, EdgeType.CALLS.value, EdgeType.INHERITS.value}:
            continue

        source_file = full_graph.nodes[source_id].get("file_path")
        target_file = full_graph.nodes[target_id].get("file_path")
        if not source_file or not target_file or source_file == target_file:
            continue

        edge_weights[(source_file, target_file, relationship)] += 1

    for (source_file, target_file, relationship), weight in edge_weights.items():
        overview.add_edge(source_file, target_file, relationship=relationship, weight=weight)

    return overview


def build_node_detail_graph(full_graph: nx.MultiDiGraph, focus_node_id: str, depth: int = 2) -> nx.MultiDiGraph:
    """Build a focused graph centered on a selected node.

    File/module nodes expand to their local file contents, while function/class
    nodes stay centered on the clicked node and its neighbors.
    """

    if focus_node_id not in full_graph:
        return nx.MultiDiGraph()

    detail = nx.MultiDiGraph()
    focus_data = full_graph.nodes[focus_node_id]
    focus_file = focus_data.get("file_path")
    focus_type = focus_data.get("type")

    included: set[str] = {focus_node_id}
    frontier: set[str] = {focus_node_id}

    if focus_file and focus_type in {NodeType.MODULE.value, "File"}:
        for node_id, data in full_graph.nodes(data=True):
            if data.get("file_path") == focus_file:
                included.add(node_id)
                frontier.add(node_id)

    for _ in range(max(depth, 0)):
        next_frontier: set[str] = set()
        for node_id in frontier:
            for _, neighbor_id, edge_data in full_graph.out_edges(node_id, data=True):
                if edge_data.get("relationship") in DETAIL_EDGE_TYPES and neighbor_id in full_graph:
                    if neighbor_id not in included:
                        next_frontier.add(neighbor_id)
                    included.add(neighbor_id)
            for neighbor_id, _, edge_data in full_graph.in_edges(node_id, data=True):
                if edge_data.get("relationship") in DETAIL_EDGE_TYPES and neighbor_id in full_graph:
                    if neighbor_id not in included:
                        next_frontier.add(neighbor_id)
                    included.add(neighbor_id)
        frontier = next_frontier

    for node_id in included:
        detail.add_node(node_id, **full_graph.nodes[node_id])

    for source_id, target_id, edge_data in full_graph.edges(data=True):
        if source_id in included and target_id in included and edge_data.get("relationship") in DETAIL_EDGE_TYPES:
            detail.add_edge(source_id, target_id, **edge_data)

    return detail


def detect_entrypoint_nodes(graph: nx.MultiDiGraph) -> list[str]:
    """Return likely root nodes, ordered from strongest entrypoint to weakest."""

    incoming_imports: dict[str, int] = defaultdict(int)
    for source_id, target_id, edge_data in graph.edges(data=True):
        if edge_data.get("relationship") == EdgeType.IMPORTS.value:
            source_type = graph.nodes[source_id].get("type")
            target_type = graph.nodes[target_id].get("type")
            if source_type in {NodeType.MODULE.value, "File"} and target_type in {NodeType.MODULE.value, "File"}:
                incoming_imports[target_id] += 1

    scored: list[tuple[int, str]] = []
    for node_id, data in graph.nodes(data=True):
        node_type = data.get("type")
        if node_type not in {NodeType.MODULE.value, "File"}:
            continue

        file_path = data.get("file_path") or node_id
        filename = Path(file_path).name.lower()
        score = 0

        if any(part in Path(file_path).parts for part in VIEWER_DIRS):
            score -= 8
        if filename in ENTRY_FILE_NAMES:
            score += 6
        if _file_has_main_guard(file_path):
            score += 8
        if incoming_imports.get(node_id, 0) == 0:
            score += 2

        entry_funcs = [
            child
            for _, child, edge_data in graph.out_edges(node_id, data=True)
            if edge_data.get("relationship") == EdgeType.DEFINES.value
            and graph.nodes[child].get("type") == NodeType.FUNCTION.value
            and graph.nodes[child].get("name") in ENTRY_FUNCTION_NAMES
        ]
        score += len(entry_funcs) * 4

        if score > 0:
            scored.append((score, node_id))

    scored.sort(key=lambda item: (-item[0], _node_sort_key(graph, item[1])))
    return [node_id for _, node_id in scored]


def build_runtime_flow_graph(
    graph: nx.MultiDiGraph,
    root_node_id: str | None = None,
    max_depth: int = 5,
) -> nx.MultiDiGraph:
    """Build a top-down flow graph starting from the most likely entry module."""

    roots = [root_node_id] if root_node_id else detect_entrypoint_nodes(graph)[:1]
    if not roots:
        roots = [next(iter(graph.nodes), None)]
    roots = [root for root in roots if root and root in graph]
    if not roots:
        return nx.MultiDiGraph()

    allowed = {
        EdgeType.DEFINES.value,
        EdgeType.CONTAINS.value,
        EdgeType.CALLS.value,
        EdgeType.INHERITS.value,
        EdgeType.IMPORTS.value,
    }

    flow = nx.MultiDiGraph()
    depth_map: dict[str, int] = {root: 0 for root in roots}
    queue = deque(roots)

    while queue:
        node_id = queue.popleft()
        node_depth = depth_map[node_id]
        if node_id not in graph:
            continue

        if node_id not in flow:
            flow.add_node(node_id, **graph.nodes[node_id], layer=node_depth)
        else:
            flow.nodes[node_id]["layer"] = min(flow.nodes[node_id].get("layer", node_depth), node_depth)

        if node_depth >= max_depth:
            continue

        for _, target_id, edge_data in graph.out_edges(node_id, data=True):
            relationship = edge_data.get("relationship")
            if relationship not in allowed or target_id not in graph:
                continue

            next_depth = node_depth + 1
            if target_id not in depth_map or next_depth < depth_map[target_id]:
                depth_map[target_id] = next_depth
                queue.append(target_id)

            if target_id not in flow:
                flow.add_node(target_id, **graph.nodes[target_id], layer=depth_map[target_id])
            else:
                flow.nodes[target_id]["layer"] = min(flow.nodes[target_id].get("layer", next_depth), depth_map[target_id])

            flow.add_edge(node_id, target_id, **edge_data)

    return flow


def layered_positions(graph: nx.MultiDiGraph, layer_key: str = "layer") -> dict[str, tuple[float, float]]:
    """Position nodes in a top-down layout using their assigned layer."""

    layers: dict[int, list[str]] = defaultdict(list)
    for node_id, data in graph.nodes(data=True):
        layer = int(data.get(layer_key, 0))
        layers[layer].append(node_id)

    positions: dict[str, tuple[float, float]] = {}
    for layer, node_ids in sorted(layers.items()):
        width = max(len(node_ids) - 1, 1)
        for index, node_id in enumerate(sorted(node_ids, key=lambda nid: _node_sort_key(graph, nid))):
            x = index - width / 2.0
            y = -float(layer)
            positions[node_id] = (x, y)
    return positions


def node_summary(graph: nx.MultiDiGraph, node_id: str) -> str:
    data = graph.nodes[node_id]
    node_type = data.get("type", "Unknown")
    file_path = data.get("file_path", "")
    parts = [f"[{node_type}] {data.get('name', node_id)}"]
    if file_path:
        parts.append(f"File: {file_path}")

    if node_type == NodeType.FUNCTION.value and data.get("source_code"):
        parts.append(usage_hint(data))
    elif data.get("docstring"):
        parts.append(f"Mô tả: {data['docstring']}")

    return "\n".join(part for part in parts if part)


def usage_hint(node_data: dict[str, Any]) -> str:
    """Generate a small usage note for function nodes."""

    source = node_data.get("source_code") or ""
    first_line = source.splitlines()[0].strip() if source else ""
    if first_line.startswith("async def "):
        signature = first_line.removeprefix("async ")
    else:
        signature = first_line

    if signature:
        return f"Cách dùng: gọi {signature}"
    return "Cách dùng: xem source code bên dưới để biết tham số và luồng xử lý."


def _build_extracted_graph(items: Sequence[Any], edges: Sequence[GraphEdge]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()

    for node in items:
        if isinstance(node, GraphNode):
            data = {
                "name": node.name,
                "type": node.type.value,
                "file_path": node.file_path,
                "line_start": node.line_start,
                "docstring": node.docstring,
                "source_code": node.source_code,
                "is_async": node.is_async,
                "decorators": list(node.decorators),
            }
            graph.add_node(node.id, **data)
        elif isinstance(node, dict) and node.get("id"):
            graph.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})

    for edge in edges:
        if isinstance(edge, GraphEdge):
            if edge.source_id not in graph or edge.target_id not in graph:
                continue
            graph.add_edge(edge.source_id, edge.target_id, relationship=edge.type.value, confidence=edge.confidence)
        elif isinstance(edge, dict):
            source_id = edge["source_id"]
            target_id = edge["target_id"]
            if source_id not in graph or target_id not in graph:
                continue
            graph.add_edge(
                source_id,
                target_id,
                relationship=edge.get("type") or edge.get("relationship"),
                confidence=edge.get("confidence", 1.0),
            )

    return graph


def _build_compat_graph(modules: Sequence[Any]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()

    function_index: dict[str, list[str]] = defaultdict(list)
    for module in modules:
        if not hasattr(module, "file_path"):
            continue
        graph.add_node(
            module.file_path,
            name=Path(module.file_path).name,
            type="File",
            file_path=module.file_path,
        )
        for function in getattr(module, "functions", []):
            function_id = f"{module.file_path}::{function.name}"
            graph.add_node(
                function_id,
                name=function.name,
                type="Function",
                file_path=module.file_path,
                calls=list(getattr(function, "calls", [])),
            )
            function_index[function.name].append(function_id)

    for module in modules:
        for function in getattr(module, "functions", []):
            source_id = f"{module.file_path}::{function.name}"
            for call_name in getattr(function, "calls", []):
                target_id = _resolve_compat_call_target(call_name, module.file_path, function_index)
                if target_id:
                    graph.add_edge(source_id, target_id, relationship=EdgeType.CALLS.value)

    return graph


def _resolve_compat_call_target(call_name: str, file_path: str, function_index: dict[str, list[str]]) -> str | None:
    candidates = function_index.get(call_name, [])
    if not candidates:
        short_name = call_name.split(".")[-1]
        candidates = function_index.get(short_name, [])
    if not candidates:
        return None

    for candidate in candidates:
        if candidate.startswith(f"{file_path}::"):
            return candidate
    return candidates[0]


def _looks_like_compat_modules(items: Sequence[Any]) -> bool:
    if not items:
        return False
    first = items[0]
    return hasattr(first, "functions") and hasattr(first, "file_path") and not hasattr(first, "id")


def _node_sort_key(graph: nx.MultiDiGraph, node_id: str) -> tuple[str, str]:
    data = graph.nodes[node_id]
    return (str(data.get("file_path", "")), str(data.get("name", node_id)))


def _file_has_main_guard(file_path: str) -> bool:
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except OSError:
        return False
    return "if __name__ == \"__main__\"" in text or "if __name__ == '__main__'" in text