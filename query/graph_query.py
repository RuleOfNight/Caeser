import networkx as nx

# Sentinel value used in the visited dict to mark a node as "currently being
# explored" — distinguishes an active cycle from a node simply seen before
# on a different branch.
_IN_PROGRESS = "__cycle__"


def get_function_calls(graph: nx.DiGraph, func_name: str) -> list[str]:
    # Return all functions that func_name directly calls (outgoing edges).
    return list(graph.successors(func_name))


def get_callers(graph: nx.DiGraph, func_name: str) -> list[str]:
    # Return all functions that directly call func_name (incoming edges).
    # Answers: "who calls this?"
    return list(graph.predecessors(func_name))


def get_call_chain(graph: nx.DiGraph, func_name: str, depth: int = 2) -> dict:
    """
    Build a call-tree rooted at func_name up to the given depth.

    Return value is a nested dict:
        {
            "a::foo": {
                "b::bar": {
                    "c::baz": {}   # depth exhausted here
                },
                "a::foo": "[cycle]"  # foo calls itself — detected and stopped
            }
        }

    Cycle handling
    --------------
    Each recursive call carries its own `path` set — the set of nodes on the
    *current* ancestor chain.  A node is a cycle only when it appears again on
    the same path (i.e. we are about to re-enter a function we have not yet
    finished expanding).  Nodes seen on *other* branches are NOT treated as
    cycles; they are expanded normally so we do not lose valid edges.

    When a cycle is detected the value is the string "[cycle]" instead of a
    dict, making cycles visible in the output rather than silently dropping them.
    """

    def _expand(node: str, remaining_depth: int, path: frozenset) -> dict | str:
        # A cycle means we reached a node that is already on the current path.
        # Mark it explicitly so callers can see the loop.
        if node in path:
            return "[cycle]"

        # Depth exhausted — stop expanding but do not mark as cycle.
        if remaining_depth == 0:
            return {}

        # Add current node to the path before going deeper.
        # frozenset ensures the parent's path is not mutated (pure functional style).
        current_path = path | {node}

        children = {}
        for callee in graph.successors(node):
            children[callee] = _expand(callee, remaining_depth - 1, current_path)

        return children

    return {func_name: _expand(func_name, depth, frozenset())}


def format_call_chain(chain: dict, indent: int = 0) -> str:
    """
    Render the nested dict returned by get_call_chain into a human-readable
    indented tree.

    Example output:
        app/main.py::run
        ├── ingestion/file_scanner.py::scan_py_files
        ├── explain/formatter.py::explain_function
        │   └── query/graph_query.py::get_function_calls
        └── graph/builder.py::build_graph  [cycle]

    Each node label is shortened to "function_name (file.py)" for readability.
    Cycle nodes are annotated with "[cycle]".
    """

    def _short(node_id: str) -> str:
        # Convert "path/to/file.py::func_name" -> "func_name (file.py)"
        parts = node_id.split("::")
        func = parts[-1]
        file = parts[0].split("/")[-1]
        return f"{func} ({file})"

    def _render(node_id: str, subtree: dict | str, prefix: str, is_last: bool) -> list[str]:
        # Choose the correct tree-drawing connector based on position
        connector = "└── " if is_last else "├── "
        # The continuation prefix for children depends on whether this is last
        extension = "    " if is_last else "│   "

        label = _short(node_id)

        # Cycle nodes carry the string "[cycle]" instead of a dict
        if subtree == "[cycle]":
            return [prefix + connector + label + "  [cycle]"]

        lines = [prefix + connector + label]

        # Recurse into children with updated prefix
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            child_is_last = (i == len(children) - 1)
            lines += _render(child_id, child_subtree, prefix + extension, child_is_last)

        return lines

    lines = []
    # The root of the chain dict is a single key (the starting function)
    for root_id, subtree in chain.items():
        lines.append(_short(root_id))
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            is_last = (i == len(children) - 1)
            lines += _render(child_id, child_subtree, "", is_last)

    return "\n".join(lines)
