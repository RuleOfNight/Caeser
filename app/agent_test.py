import os
import sys
import io
import pickle

# Fix encoding cho Windows console để in tiếng Việt và ký tự đặc biệt
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Thêm thư mục gốc của dự án vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools import setup_tool_globals
from agents.workflow import build_caeser_graph
from indexing.vector_store import VectorStore
from langchain_core.messages import HumanMessage

def run_caeser():
    print("[*] Đang khởi động Hệ thống Đặc vụ Caeser (Multi-Agent ARAG)...")
    
    # 1. Nạp dữ liệu Vector và Graph từ Cache
    vstore = VectorStore()
    
    if not os.path.exists("db/graph_cache.pkl"):
        print("[-] Lỗi: Không tìm thấy db/graph_cache.pkl. Hãy chạy file app/main.py để build đồ thị trước!")
        sys.exit(1)
        
    with open("db/graph_cache.pkl", "rb") as f:
        graph = pickle.load(f)
        
    # Nạp dữ liệu vào không gian của Đặc vụ
    setup_tool_globals(graph, vstore)
    
    # 2. Khởi tạo Đồ thị LangGraph
    app = build_caeser_graph()
    print("\n[+] CAESER MULTI-AGENT ONLINE. (Sử dụng mô hình Local)")

    # 3. Vòng lặp giao tiếp
    while True:
        try:
            user_input = input("\nBạn: ")
            if user_input.lower() in ["exit", "quit"]: 
                break
                
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # Cấu hình giới hạn đệ quy cao để tránh ngắt sớm khi Agent xử lý nhiều bước
            config = {"recursion_limit": 50}
            
            print("\n" + "-"*50)
            
            # Lắng nghe từng bước xử lý của hệ thống
            for event in app.stream(inputs, config=config):
                for node_name, state in event.items():
                    print(f"\n▶ [Hệ thống] -> {node_name} đang xử lý...")
                    
                    if not state.get("messages"):
                        continue
                        
                    msg = state["messages"][-1]
                    
                    # Nếu là Tool Node chạy xong
                    if node_name == "tools":
                        print("  |_ Đã thực thi công cụ và lấy kết quả thành công.")
                        continue
                        
                    # Nếu là các Agent xử lý
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tools_called = [tc['name'] for tc in msg.tool_calls]
                        print(f"  |_ Gọi công cụ: {', '.join(tools_called)}")
                    elif msg.content:
                        # In ra nội dung Agent nói
                        print(f"[{node_name.upper()}]:\n{msg.content}")
                        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[-] Lỗi thực thi: {e}")
            continue

if __name__ == "__main__":
    run_caeser()