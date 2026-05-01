import networkx as nx

def get_node_context(graph: nx.MultiDiGraph, node_id: str) -> dict:
    """Lấy thông tin chi tiết của một node."""
    if node_id not in graph:
        return {}
    node_data = graph.nodes[node_id]
    return {
        "id": node_id,
        "name": node_data.get("name"),
        "type": node_data.get("type"),
        "file_path": node_data.get("file_path"),
        "docstring": node_data.get("content", ""),
        "source_code": node_data.get("source_code", "N/A")
    }

def get_function_calls(graph: nx.MultiDiGraph, node_id: str) -> list[str]:
    """Lấy danh sách các hàm mà node_id đang gọi."""
    if node_id not in graph: return []
    return [v for _, v, data in graph.out_edges(node_id, data=True) if data.get("relationship") == "CALLS"]

def get_call_chain(graph: nx.MultiDiGraph, start_node_id: str, depth: int = 2) -> dict:
    """Dựng cây gọi hàm (Call Tree), chặn lặp vòng (cycle)."""
    def _expand(node: str, remaining_depth: int, path: frozenset) -> dict | str:
        if node in path: return "[cycle]"
        if remaining_depth == 0: return {}

        current_path = path | {node}
        children = {}
        callees = [v for _, v, data in graph.out_edges(node, data=True) if data.get("relationship") == "CALLS"]
        
        for callee in callees:
            children[callee] = _expand(callee, remaining_depth - 1, current_path)
        return children

    return {start_node_id: _expand(start_node_id, depth, frozenset())}

def format_call_chain(chain: dict) -> str:
    """Format Call Tree ra dạng text có nhánh cây."""
    def _short(node_id: str) -> str:
        content = node_id.split(":", 1)[-1]
        if "::" in content:
            file_path, name = content.split("::", 1)
            file_name = file_path.split("/")[-1].split("\\")[-1]
            return f"{name} ({file_name})"
        return content

    def _render(node_id: str, subtree: dict | str, prefix: str, is_last: bool) -> list[str]:
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "
        label = _short(node_id)
        if subtree == "[cycle]": return [prefix + connector + label + "  [cycle]"]
        lines = [prefix + connector + label]
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            lines += _render(child_id, child_subtree, prefix + extension, i == len(children)-1)
        return lines

    lines = []
    for root_id, subtree in chain.items():
        lines.append(_short(root_id))
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            lines += _render(child_id, child_subtree, "", i == len(children)-1)
    return "\n".join(lines)

def search_jit_context(graph: nx.MultiDiGraph, vector_store, query_text: str, top_k: int = 5) -> list[dict]:
    """Tìm kiếm lai JIT (Just-in-Time) bằng RRF, trả về context Node để đưa cho LLM."""
    # 1. Tìm kiếm Vector
    vector_ids = vector_store.search_vector(query_text, top_k=top_k)
    
    # 2. Tìm kiếm BM25
    bm25_ids = vector_store.search_bm25(query_text, top_k=top_k)
    
    # 3. Dung hợp RRF (Reciprocal Rank Fusion)
    k_penalty = 60
    rrf_scores = {}
    
    for rank, doc_id in enumerate(vector_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_penalty + rank + 1)
        
    for rank, doc_id in enumerate(bm25_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_penalty + rank + 1)
        
    # Sắp xếp lấy Top K kết quả tốt nhất
    fused_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    top_ids = [item[0] for item in fused_results][:top_k]
    
    # 4. Truy xuất context chi tiết từ Graph
    return [get_node_context(graph, node_id) for node_id in top_ids if node_id in graph]