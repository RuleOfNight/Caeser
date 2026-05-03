import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Optional

from extraction.models import FileModule
from query.graph_query import get_call_chain


def build_graph(modules: List[FileModule]) -> nx.DiGraph:
    g = nx.DiGraph()
    last_seg_map: dict[str, list[str]] = {}  # func_name -> [node_ids] dùng để resolve call

    # Lượt 1: thêm tất cả node trước để lượt 2 có thể tham chiếu
    for mod in modules:
        for fn in mod.functions:
            node_id = f"{fn.file}::{fn.name}"
            g.add_node(node_id, name=fn.name, file=fn.file)
            last_seg_map.setdefault(fn.name, []).append(node_id)

    # Lượt 2: thêm edge, bỏ qua call tới hàm không tồn tại trong project
    for mod in modules:
        for fn in mod.functions:
            caller_id = f"{fn.file}::{fn.name}"
            for call in fn.calls:
                callee_id = _resolve_call(call, last_seg_map)
                if callee_id and callee_id in g:
                    g.add_edge(caller_id, callee_id)

    return g


def _resolve_call(call: str, last_seg_map: dict) -> Optional[str]:
    # "obj.method" được resolve theo segment cuối để khớp với tên hàm
    seg = call.split(".")[-1]
    candidates = last_seg_map.get(seg, [])
    return candidates[0] if candidates else None


def _collect_chain_nodes(chain) -> set:
    nodes = set()
    if isinstance(chain, str):
        return nodes  # gặp "[cycle]" sentinel th dừng đệ quy
    for node_id, subtree in chain.items():
        nodes.add(node_id)
        nodes |= _collect_chain_nodes(subtree)
    return nodes


def _short_label(node_id: str) -> str:
    if "::" in node_id:
        file_path, name = node_id.split("::", 1)
        file_name = file_path.split("/")[-1].split("\\")[-1]
        return f"{name} ({file_name})"
    return node_id


def _resolve_node(g: nx.DiGraph, node_id: str) -> Optional[str]:
    if node_id in g:
        return node_id
    # cho phép truyền tên ngắn "foo" thay vì full id "file.py::foo"
    matches = [n for n in g.nodes if n.split("::")[-1] == node_id]
    return matches[0] if matches else None


def visualize_subgraph(
    g: nx.DiGraph,
    node_id: str,
    depth: int = 2,
    output_path: Optional[str] = None,
):
    full_id = _resolve_node(g, node_id)
    if full_id is None:
        return

    chain = get_call_chain(g, full_id, depth=depth)
    sub_nodes = _collect_chain_nodes(chain)
    subgraph = g.subgraph(sub_nodes)

    pos = nx.spring_layout(subgraph)
    labels = {n: _short_label(n) for n in subgraph.nodes}

    nx.draw_networkx_nodes(subgraph, pos)
    nx.draw_networkx_edges(subgraph, pos)
    nx.draw_networkx_labels(subgraph, pos, labels=labels)

    plt.savefig(output_path, dpi=150)
    plt.close()


class Neo4jManager:
    """Manages Neo4j connection for graph storage."""
    def __init__(self, uri: str = None, user: str = None, password: str = None):           
        import os
        uri      = uri      or os.getenv("NEO4J_URI")        
        user     = user     or os.getenv("NEO4J_USER")                        
        password = password or os.getenv("NEO4J_PASSWORD")
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"[-] Cannot connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def load_graph(self, g: nx.DiGraph):
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")  # xoá sạch trước khi load để đảm bảo idempotent
            for node_id, data in g.nodes(data=True):
                session.run(
                    "MERGE (n:Function {id: $id}) SET n.name = $name, n.file = $file",
                    id=node_id, name=data.get("name"), file=data.get("file"),
                )
            for u, v in g.edges():
                session.run(
                    "MATCH (a {id: $u}), (b {id: $v}) MERGE (a)-[:CALLS]->(b)",
                    u=u, v=v,
                )
        print("[+] Graph loaded to Neo4j.")
