import json
import re
from pathlib import Path

# Ký tự không hợp lệ trong tên file Windows/Mac
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str) -> str:
    return _UNSAFE.sub("_", name)


def _wikilink(node: dict) -> str:
    # Obsidian match wikilink theo filename, không phải node ID
    # nên dùng name (= tên file .md) thay vì id
    return f"[[{_safe(node['name'])}]]"


def export(graph_path: str, vault_path: str) -> None:
    graph = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    project_name = graph["project"]
    nodes = {n["id"]: n for n in graph["nodes"]}

    # Chỉ build adjacency cho edges đã resolved (confidence > 0.0)
    # Edge confidence=0.0 là external lib hoặc ambiguous — tạo wikilink gãy nếu giữ lại
    outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}
    incoming: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for edge in graph["edges"]:
        if edge["confidence"] > 0.0:
            src, tgt = edge["source_id"], edge["target_id"]
            if src in outgoing and tgt in incoming:
                outgoing[src].append(edge)
                incoming[tgt].append(edge)

    vault_root = Path(vault_path) / _safe(project_name)
    for subdir in ("modules", "classes", "functions"):
        (vault_root / subdir).mkdir(parents=True, exist_ok=True)

    count = 0
    for node_id, node in nodes.items():
        content = _render(node, nodes, outgoing, incoming)
        subdir = {"Module": "modules", "Class": "classes", "Function": "functions"}.get(node["type"], "misc")
        out_file = vault_root / subdir / (_safe(node["name"]) + ".md")
        out_file.write_text(content, encoding="utf-8")
        count += 1

    print(f"[+] Obsidian vault -> {vault_root}")
    print(f"    Files: {count}")


def _render(node, nodes, outgoing, incoming) -> str:
    t = node["type"]
    if t == "Module":
        return _module(node, nodes, outgoing, incoming)
    if t == "Class":
        return _class(node, nodes, outgoing, incoming)
    if t == "Function":
        return _function(node, nodes, outgoing, incoming)
    return ""


def _edges_of(nid, adj, edge_type):
    return [e for e in adj.get(nid, []) if e["type"] == edge_type]


def _targets(edges, nodes):
    return [nodes[e["target_id"]] for e in edges if e["target_id"] in nodes]


def _sources(edges, nodes):
    return [nodes[e["source_id"]] for e in edges if e["source_id"] in nodes]


def _module(node, nodes, outgoing, incoming) -> str:
    nid = node["id"]
    lines = [f"# {node['name']}", f"**Type:** Module", f"**File:** `{node['file_path']}`", ""]

    imports = _targets(_edges_of(nid, outgoing, "IMPORTS"), nodes)
    if imports:
        lines += ["## Imports"] + [f"- {_wikilink(n)}" for n in imports] + [""]

    defines = _edges_of(nid, outgoing, "DEFINES")
    classes = [nodes[e["target_id"]] for e in defines if e["target_id"] in nodes and nodes[e["target_id"]]["type"] == "Class"]
    funcs   = [nodes[e["target_id"]] for e in defines if e["target_id"] in nodes and nodes[e["target_id"]]["type"] == "Function"]

    if classes:
        lines += ["## Classes"] + [f"- {_wikilink(c)}" for c in classes] + [""]
    if funcs:
        lines += ["## Functions"] + [f"- {_wikilink(f)}" for f in funcs] + [""]

    imported_by = _sources(_edges_of(nid, incoming, "IMPORTS"), nodes)
    if imported_by:
        lines += ["## Imported by"] + [f"- {_wikilink(m)}" for m in imported_by] + [""]

    return "\n".join(lines)


def _class(node, nodes, outgoing, incoming) -> str:
    nid = node["id"]
    lines = [
        f"# {node['name']}",
        f"**Type:** Class",
        f"**File:** `{node['file_path']}`",
        f"**Line:** {node['line_start']}",
        "",
    ]

    if node.get("docstring"):
        lines += ["## Docstring", node["docstring"], ""]

    methods = _targets(_edges_of(nid, outgoing, "CONTAINS"), nodes)
    if methods:
        lines += ["## Methods"] + [f"- {_wikilink(m)}" for m in methods] + [""]

    inherits = _targets(_edges_of(nid, outgoing, "INHERITS"), nodes)
    if inherits:
        lines += ["## Inherits"] + [f"- {_wikilink(b)}" for b in inherits] + [""]

    defined_in = _sources(_edges_of(nid, incoming, "DEFINES"), nodes)
    if defined_in:
        lines += ["## Defined in"] + [f"- {_wikilink(m)}" for m in defined_in] + [""]

    return "\n".join(lines)


def _function(node, nodes, outgoing, incoming) -> str:
    nid = node["id"]
    type_label = "Async Function" if node.get("is_async") else "Function"
    lines = [
        f"# {node['name']}",
        f"**Type:** {type_label}",
        f"**File:** `{node['file_path']}`",
        f"**Line:** {node['line_start']}",
    ]
    if node.get("decorators"):
        lines.append(f"**Decorators:** {', '.join(node['decorators'])}")
    lines.append("")

    if node.get("docstring"):
        lines += ["## Docstring", node["docstring"], ""]

    # Kiểm tra CONTAINS trước DEFINES để method hiện "Class" thay vì "Module"
    for etype, label in (("CONTAINS", "Class"), ("DEFINES", "Module")):
        containers = _sources(_edges_of(nid, incoming, etype), nodes)
        if containers:
            lines += [f"## {label}"] + [f"- {_wikilink(c)}" for c in containers] + [""]
            break

    calls = _targets(_edges_of(nid, outgoing, "CALLS"), nodes)
    if calls:
        lines += ["## Calls"] + [f"- {_wikilink(c)}" for c in calls] + [""]

    callers = _sources(_edges_of(nid, incoming, "CALLS"), nodes)
    if callers:
        lines += ["## Called by"] + [f"- {_wikilink(c)}" for c in callers] + [""]

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out",   required=True)
    args = parser.parse_args()
    export(args.graph, args.out)
