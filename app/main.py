import os
import sys
import io
import argparse
import networkx as nx
from collections import Counter

# Fix encoding cho Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.file_scanner import scan_py_files
from extraction.extractor import extract_from_file
from graph.builder import build_graph, visualize_architecture, Neo4jManager
from query.graph_query import get_call_chain, format_call_chain, search_jit_context
from indexing.vector_store import VectorStore
from app.graph_viewer import launch_graph_viewer

def run(repo_path: str):
    """Pipeline hoàn chỉnh: Scan -> Extract -> Graph -> Index -> Save DB -> Query."""
    print(f"[*] Đang quét thư mục: {os.path.abspath(repo_path)}")
    files = scan_py_files(repo_path)
    
    if not files:
        print("[-] Không tìm thấy file Python nào.")
        return

    all_nodes = []
    all_edges = []

    print(f"[*] Đang phân tích AST và trích xuất thực thể từ {len(files)} file...")
    for f in files:
        nodes, edges = extract_from_file(f)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    print(f"[*] Đang dựng Knowledge Graph với {len(all_nodes)} Nodes và {len(all_edges)} Edges...")
    graph = build_graph(all_nodes, all_edges)

    node_types = nx.get_node_attributes(graph, 'type').values()
    type_counts = Counter(node_types)
    print(f"[+] Tổng số Nodes trong RAM: {len(graph.nodes)}")
    print(f"[+] Phân bổ Node: {dict(type_counts)}")

    if len(graph.nodes) == 0:
        print("[-] Đồ thị rỗng. Không có dữ liệu để hiển thị.")
        return

    os.makedirs("db", exist_ok=True) 

    # LƯU 1: Nhúng vào VectorDB và BM25 (ChromaDB)
    vstore = VectorStore()
    vstore.add_nodes(all_nodes)
    
    # # LƯU 2: GraphDB (Đồng bộ lên Neo4j)
    # neo4j_db = Neo4jManager(password="password") # Đổi password theo Neo4j của bạn
    # neo4j_db.export_from_networkx(graph)
    # neo4j_db.close()

    # LƯU 3: Vẽ bản đồ kiến trúc
    output_img = "db/full_architecture_map.png"
    print(f"[*] Đang vẽ bản đồ kiến trúc toàn diện và lưu tại: {output_img}")
    visualize_architecture(graph, output_path=output_img)

    # =========================================================
    # KIỂM THỬ: ĐẶC VỤ AI TÌM KIẾM NGỮ CẢNH (JIT CONTEXT RRF)
    # =========================================================
    print("\n" + "="*50)
    print(" KIỂM THỬ TÌM KIẾM HYBRID SEARCH (VECTOR + BM25)")
    print("="*50)
    
    ai_query = "find extractor to extract function definitions"
    print(f"[*] Truy vấn của AI: '{ai_query}'")
    
    top_contexts = search_jit_context(graph, vstore, ai_query, top_k=2)
    
    for i, ctx in enumerate(top_contexts, 1):
        print(f"\n--- [Kết quả {i}: {ctx['name']}] ---")
        print(f"Type: {ctx['type']} | File: {ctx['file_path']}")
        print(f"Docstring: {ctx['docstring']}")
        
        chain = get_call_chain(graph, ctx['id'], depth=1)
        print("\nCấu trúc liên kết:")
        print(format_call_chain(chain))


def main():
    parser = argparse.ArgumentParser(description="Caeser project analyzer and local graph viewer")
    parser.add_argument("repo_path", nargs="?", default=".", help="Repository path to analyze")
    parser.add_argument("--viewer", action="store_true", help="Open the interactive desktop graph viewer")
    args = parser.parse_args()

    if args.viewer:
        launch_graph_viewer(args.repo_path)
        return

    run(args.repo_path)

if __name__ == "__main__":
    main()