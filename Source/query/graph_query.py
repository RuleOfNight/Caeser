import networkx as nx


def get_node_context(graph: nx.DiGraph, node_id: str) -> dict:
    if node_id not in graph:
        return {}
    data = graph.nodes[node_id]
    return {"id": node_id, "name": data.get("name"), "file": data.get("file")}


def get_function_calls(graph: nx.DiGraph, node_id: str) -> list[str]:
    return list(graph.successors(node_id))


def get_callers(graph: nx.DiGraph, node_id: str) -> list[str]:
    return list(graph.predecessors(node_id))


def get_call_chain(graph: nx.DiGraph, start_node_id: str, depth: int = 2) -> dict:
    # path lưu tập root node, trả về "[cycle]" thay vì dict khi phát hiện cycle
    def _expand(node: str, remaining_depth: int, path: frozenset):
        if node in path:
            return "[cycle]"
        if remaining_depth == 0:
            return {}
        current_path = path | {node}
        return {
            callee: _expand(callee, remaining_depth - 1, current_path)
            for callee in graph.successors(node)
        }

    return {start_node_id: _expand(start_node_id, depth, frozenset())}


def format_call_chain(chain: dict) -> str:
    def _short(node_id: str) -> str:
        if "::" in node_id:
            file_path, name = node_id.split("::", 1)
            file_name = file_path.split("/")[-1].split("\\")[-1]
            return f"{name} ({file_name})"
        return node_id

    def _render(node_id: str, subtree, prefix: str, is_last: bool) -> list[str]:
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "
        label = _short(node_id)
        if subtree == "[cycle]":
            return [prefix + connector + label + "  [cycle]"]
        lines = [prefix + connector + label]
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            lines += _render(child_id, child_subtree, prefix + extension, i == len(children) - 1)
        return lines

    lines = []
    for root_id, subtree in chain.items():
        lines.append(_short(root_id))
        items = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(items):
            lines += _render(child_id, child_subtree, "", i == len(items) - 1)
    return "\n".join(lines)
