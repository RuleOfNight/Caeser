import networkx as nx
from typing import List

from extraction.models import GraphEdge, GraphNode

# add các nodes và edges đã resolve (có confidence > 0)
def build_graph(nodes: List[GraphNode], edges: List[GraphEdge]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    node_ids = set()

    for node in nodes:
        g.add_node(
            node.id,
            name=node.name,
            type=node.type.value,
            file_path=node.file_path,
            content=node.docstring or "",
            source_code="",
        )
        node_ids.add(node.id)

    for edge in edges:
        if (edge.confidence > 0.0
                and edge.source_id in node_ids
                and edge.target_id in node_ids):
            g.add_edge(
                edge.source_id,
                edge.target_id,
                relationship=edge.type.value,
                confidence=edge.confidence,
            )

    return g
