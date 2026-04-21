from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from agents.tools import search_architecture, read_full_file_from_db, safe_patch_file
from langchain_ollama import ChatOllama
import operator
import json

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_agent: str

llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0)

# ==========================================
# PHÂN QUYỀN VŨ KHÍ RÕ RÀNG
# ==========================================
architect_tools = [search_architecture, read_full_file_from_db]
coder_tools = [safe_patch_file]
all_tools = architect_tools + coder_tools

llm_architect = llm.bind_tools(architect_tools)
llm_coder = llm.bind_tools(coder_tools)

# ==========================================
# CÁC ĐẶC VỤ (KỶ LUẬT THÉP)
# ==========================================

def planner_node(state: AgentState):
    """Planner bị cấm tuyệt đối việc sử dụng JSON."""
    sys_msg = AIMessage(content="""Bạn là Trưởng nhóm (Planner). BẠN KHÔNG CÓ BẤT KỲ CÔNG CỤ NÀO.
TUYỆT ĐỐI KHÔNG ĐƯỢC IN RA BẤT KỲ ĐỊNH DẠNG JSON HAY NGOẶC NHỌN {} NÀO.

Nhiệm vụ của bạn là đọc lịch sử và CHỈ ĐƯỢC TRẢ LỜI ĐÚNG 1 TRONG 3 CÂU VĂN BẢN SAU:
1. Nếu chưa có mã nguồn chi tiết -> Trả lời: "CHUYỂN GIAO CHO: ARCHITECT"
2. Nếu lịch sử ĐÃ CÓ dòng chữ "--- TOÀN BỘ CODE CỦA FILE" -> Trả lời: "CHUYỂN GIAO CHO: CODER"
3. Nếu Coder báo đã vá lỗi xong hoặc lỗi thất bại -> Trả lời: "KẾT THÚC"
""")
    response = llm.invoke([sys_msg] + state["messages"])
    return {"messages": [response], "current_agent": "planner"}

def architect_node(state: AgentState):
    """Architect bị cấm gọi 1 công cụ 2 lần liên tiếp."""
    sys_msg = AIMessage(content="""Bạn là Kiến trúc sư (Architect). 
LƯU Ý CỰC KỲ QUAN TRỌNG: BẠN KHÔNG BAO GIỜ ĐƯỢC GỌI 1 CÔNG CỤ 2 LẦN LIÊN TIẾP! HÃY LÀM THEO ĐÚNG 3 BƯỚC:

- BƯỚC 1: Gọi 'search_architecture' với tên file (ví dụ: "agent_test.py").
- BƯỚC 2: Khi thấy hệ thống trả về đường dẫn file_path, BẠN PHẢI DỪNG TÌM KIẾM NGAY LẬP TỨC. Hãy chuyển sang gọi 'read_full_file_from_db' với file_path đó.
- BƯỚC 3: KHI ĐÃ ĐỌC XONG (thấy hệ thống trả về toàn bộ code), BẠN KHÔNG ĐƯỢC GỌI TOOL NỮA. Hãy trả lời bằng một câu văn: "TÔI ĐÃ LẤY XONG CODE, XIN MỜI CODER."
""")
    response = llm_architect.invoke([sys_msg] + state["messages"])
    response = _fix_json_tool_calls(response, "arch_")
    return {"messages": [response], "current_agent": "architect"}

def coder_node(state: AgentState):
    """Coder chỉ được chốt hạ 1 lần duy nhất."""
    sys_msg = AIMessage(content="""Bạn là Lập trình viên (Coder). 
Nhiệm vụ: Hãy cuộn lên lịch sử, tìm phần "--- TOÀN BỘ CODE CỦA FILE". Copy chính xác một đoạn code cũ vào 'old_code_snippet' và viết code mới vào 'new_code_snippet' thông qua công cụ 'safe_patch_file'.

QUY TẮC SỐNG CÒN:
- BẠN CHỈ ĐƯỢC GỌI 'safe_patch_file' ĐÚNG 1 LẦN DUY NHẤT.
- Sau khi công cụ trả về kết quả thành công hoặc thất bại, BẠN KHÔNG ĐƯỢC GỌI TOOL NỮA. Hãy trả lời bằng văn bản: "TÔI ĐÃ SỬA XONG, TRẢ VỀ PLANNER."
""")
    response = llm_coder.invoke([sys_msg] + state["messages"])
    response = _fix_json_tool_calls(response, "code_")
    return {"messages": [response], "current_agent": "coder"}

def _fix_json_tool_calls(response, id_prefix):
    """Hàm cứu cánh bắt lỗi khi Model 3B nhả JSON text thay vì Tool Call."""
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        if isinstance(response.content, str) and "{" in response.content and "name" in response.content:
            try:
                s = response.content[response.content.find('{'):response.content.rfind('}')+1]
                parsed = json.loads(s)
                args = parsed.get("args", parsed.get("arguments", {}))
                response.tool_calls = [{"name": parsed["name"], "args": args, "id": f"{id_prefix}123"}]
                response.content = "" 
            except: pass
    return response

# ==========================================
# ĐIỀU PHỐI (ROUTER)
# ==========================================

def orchestrator_router(state: AgentState):
    last_msg = state["messages"][-1]
    
    # 1. Nếu có tool calls -> Đi thẳng vào node tools
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tools"
        
    # 2. Xử lý điều phối từ Planner
    if state["current_agent"] == "planner":
        text = str(last_msg.content).upper()
        if "ARCHITECT" in text: return "Architect"
        if "CODER" in text: return "Coder"
        return END

    # 3. Các Agent làm xong phần việc (bằng cách nói văn bản, không gọi tool nữa) -> Trả về Planner đánh giá tiếp
    return "Planner"

def route_tools(state: AgentState):
    # Tool chạy xong thì trả kết quả lại cho đúng người gọi nó
    if state["current_agent"] == "architect": return "Architect"
    if state["current_agent"] == "coder": return "Coder"
    return "Planner"

def build_caeser_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("Planner", planner_node)
    workflow.add_node("Architect", architect_node)
    workflow.add_node("Coder", coder_node)
    workflow.add_node("tools", ToolNode(all_tools))

    workflow.add_edge(START, "Planner")
    workflow.add_conditional_edges("Planner", orchestrator_router, {"Architect": "Architect", "Coder": "Coder", END: END})
    workflow.add_conditional_edges("Architect", orchestrator_router, {"tools": "tools", "Planner": "Planner"})
    workflow.add_conditional_edges("Coder", orchestrator_router, {"tools": "tools", "Planner": "Planner"})
    workflow.add_conditional_edges("tools", route_tools, {"Architect": "Architect", "Coder": "Coder", "Planner": "Planner"})
    
    return workflow.compile()