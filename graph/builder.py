import networkx as nx
import matplotlib.pyplot as plt
from typing import List
from neo4j import GraphDatabase

from extraction.models import GraphNode, GraphEdge
from query.graph_query import get_call_chain

def build_graph(nodes: List[GraphNode], edges: List[GraphEdge]) -> nx.MultiDiGraph:
    """Xây dựng đồ thị đa nhãn và nạp đầy đủ thuộc tính vào từng Node."""
    graph = nx.MultiDiGraph()

    for node in nodes:
        graph.add_node(
            node.id, 
            name=node.name, 
            type=node.type.value, 
            file_path=node.file_path,
            source_code=node.source_code,
            content=node.content          
        )

    for edge in edges:
        graph.add_edge(
            edge.source_id, 
            edge.target_id, 
            relationship=edge.type.value
        )

    return graph

class Neo4jManager:
    """Quản lý kết nối tới Neo4j Graph Database để AI truy vấn bằng Cypher."""
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"[-] Không thể kết nối Neo4j (Vui lòng bật Neo4j Desktop): {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def export_from_networkx(self, nx_graph: nx.MultiDiGraph):
        """Đồng bộ toàn bộ đồ thị từ RAM (NetworkX) lên DB vật lý (Neo4j)."""
        if not self.driver: return

        print("[*] Đang đồng bộ cấu trúc lên Neo4j Database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            
            for node_id, data in nx_graph.nodes(data=True):
                cypher = f"""
                CREATE (n:{data['type']} {{
                    id: $id, name: $name, file_path: $file_path
                }})
                """
                session.run(cypher, id=node_id, name=data.get('name'), file_path=data.get('file_path'))
            
            for u, v, data in nx_graph.edges(data=True):
                rel_type = data['relationship']
                cypher = f"""
                MATCH (a {{id: $u}}), (b {{id: $v}})
                CREATE (a)-[:{rel_type}]->(b)
                """
                session.run(cypher, u=u, v=v)
        print("[+] Đã đồng bộ Neo4j thành công!")

def _collect_nodes(chain: dict | str) -> set[str]:
    """Đệ quy qua dict của get_call_chain để lấy ra các node ID."""
    nodes = set()
    if isinstance(chain, str):
        return nodes
    for node_id, subtree in chain.items():
        nodes.add(node_id)
        nodes |= _collect_nodes(subtree)
    return nodes

def visualize_architecture(graph: nx.MultiDiGraph, output_path: str = "architecture_map.png"):
    """Vẽ bản đồ kiến trúc toàn diện của dự án."""
    plt.figure(figsize=(24, 16)) 
    
    pos = nx.spring_layout(graph, k=0.8, iterations=100, seed=42)
    
    color_map = {
        "File": "#1f77b4",       
        "Class": "#2ca02c",      
        "Function": "#d62728",   
        "Variable": "#bcbd22",   
        "Dependency": "#7f7f7f"  
    }
    
    for n_type, color in color_map.items():
        n_list = [n for n, d in graph.nodes(data=True) if d.get("type") == n_type]
        if n_list:
            size = 3500 if n_type == "File" else 1200
            nx.draw_networkx_nodes(graph, pos, nodelist=n_list, node_color=color, 
                                 node_size=size, alpha=0.9, label=n_type)

    edge_styles = {
        "CONTAINS": {"color": "#aec7e8", "style": "dashed", "width": 1.0},
        "CALLS": {"color": "#ff9896", "style": "solid", "width": 2.0},
        "INHERITS": {"color": "#98df8a", "style": "solid", "width": 1.5}
    }

    for e_type, style in edge_styles.items():
        e_list = [(u, v) for u, v, d in graph.edges(data=True) if d.get("relationship") == e_type]
        if e_list:
            nx.draw_networkx_edges(graph, pos, edgelist=e_list, edge_color=style["color"],
                                 style=style["style"], width=style["width"], 
                                 arrows=True, arrowsize=20, connectionstyle="arc3,rad=0.1")

    labels = {n: d.get("name", n) for n, d in graph.nodes(data=True)}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8, font_weight="bold", font_family="sans-serif")

    plt.title("Bản đồ Kiến trúc Toàn diện Dự án Caeser", fontsize=25, pad=20)
    plt.legend(scatterpoints=1, loc="upper left", fontsize=15)
    plt.axis("off")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[+] Đã tạo bản đồ kiến trúc tại: {output_path}")