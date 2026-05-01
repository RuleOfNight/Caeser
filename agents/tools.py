import os
from langchain_core.tools import tool
from query.graph_query import search_jit_context, get_node_context, get_call_chain, format_call_chain

GLOBAL_GRAPH = None
GLOBAL_VSTORE = None

def setup_tool_globals(graph, vstore):
    global GLOBAL_GRAPH, GLOBAL_VSTORE
    GLOBAL_GRAPH = graph
    GLOBAL_VSTORE = vstore

@tool
def search_architecture(query: str, top_k: int = 3) -> str:
    """[DÀNH CHO ARCHITECT] Tìm kiếm các hàm/lớp liên quan để lấy file_path."""
    if not GLOBAL_GRAPH or not GLOBAL_VSTORE: return "Lỗi: Hệ thống chưa khởi tạo."
    results = search_jit_context(GLOBAL_GRAPH, GLOBAL_VSTORE, query, top_k)
    if not results: return "Không tìm thấy dữ liệu khớp."
    
    out = []
    for ctx in results:
        out.append(f"- Thực thể: {ctx['name']} | ID: {ctx['id']} | Thuộc File: {ctx['file_path']}")
    return "\n".join(out)

@tool
def read_full_file_from_db(file_path: str) -> str:
    """[DÀNH CHO ARCHITECT & CODER] Rút toàn bộ mã nguồn thô của file từ Graph DB."""
    if not GLOBAL_GRAPH: return "Lỗi: Hệ thống chưa khởi tạo."
    
    # Định dạng ID của file node trong extractor.py của bạn là f"file:{file_path}"
    # Đôi khi đường dẫn có thể bị sai lệch (dấu \ hoặc /), ta tìm kiếm linh hoạt
    for node_id, data in GLOBAL_GRAPH.nodes(data=True):
        if data.get("type") == "File" and file_path in data.get("file_path", ""):
            return f"--- TOÀN BỘ CODE CỦA FILE: {data['file_path']} ---\n{data['source_code']}"
            
    # Fallback: Nếu không tìm thấy trong Graph, đọc thẳng từ ổ cứng
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f"--- TOÀN BỘ CODE CỦA FILE: {file_path} ---\n{f.read()}"
    except Exception as e:
        pass
        
    return f"Lỗi: Không tìm thấy nội dung file {file_path} trong Database lẫn ổ cứng."

@tool
def safe_patch_file(file_path: str, old_code_snippet: str, new_code_snippet: str) -> str:
    """[DÀNH CHO CODER] Thay thế chính xác đoạn code cũ bằng đoạn code mới."""
    if not os.path.exists(file_path):
        return f"[-] Lỗi: File {file_path} không tồn tại."
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if old_code_snippet not in content:
        return "[-] Lỗi: Đoạn 'old_code_snippet' bạn cung cấp không khớp 100% với code trong file. Coder hãy dùng tool 'read_full_file_from_db' để đọc lại code gốc và copy cho chính xác từng khoảng trắng."
        
    new_content = content.replace(old_code_snippet, new_code_snippet, 1)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    return f"[+] VÁ LỖI THÀNH CÔNG: Đã cập nhật file {file_path}."

def get_caeser_tools():
    return [search_architecture, read_full_file_from_db, safe_patch_file]