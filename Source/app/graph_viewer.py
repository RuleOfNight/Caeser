from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.builder import (  # noqa: E402
    build_project_graph,
    build_overview_graph,
    build_node_detail_graph,
    layered_positions,
    node_summary,
    usage_hint,
)


NODE_COLORS = {
    "Module": "#1f77b4",
    "File": "#1f77b4",
    "Class": "#2ca02c",
    "Function": "#d62728",
}

EDGE_STYLES = {
    "CALLS": {"color": "#ff9896", "style": "solid", "width": 1.8},
    "DEFINES": {"color": "#aec7e8", "style": "dashed", "width": 1.0},
    "CONTAINS": {"color": "#98df8a", "style": "dashed", "width": 1.0},
    "IMPORTS": {"color": "#c5b0d5", "style": "dotted", "width": 1.0},
    "INHERITS": {"color": "#ffbb78", "style": "solid", "width": 1.4},
}


@dataclass
class RootOption:
    label: str
    node_id: str


@dataclass
class ViewState:
    graph: nx.MultiDiGraph
    title: str
    selected_node_id: str | None = None
    file_path: str | None = None
    focus_node_id: str | None = None
    detail_depth: int = 0


class GraphViewerApp:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.root = tk.Tk()
        self.root.title("CAESER Graph Viewer")
        self.root.geometry("1720x1040")

        self.full_graph = self._build_full_graph()
        self.node_visibility: dict[str, tk.BooleanVar] = {
            "Module": tk.BooleanVar(value=True),
            "File": tk.BooleanVar(value=True),
            "Class": tk.BooleanVar(value=True),
            "Function": tk.BooleanVar(value=True),
        }
        self.edge_visibility: dict[str, tk.BooleanVar] = {
            "CALLS": tk.BooleanVar(value=True),
            "DEFINES": tk.BooleanVar(value=True),
            "CONTAINS": tk.BooleanVar(value=True),
            "IMPORTS": tk.BooleanVar(value=False),
            "INHERITS": tk.BooleanVar(value=False),
        }

        self.view_stack: list[ViewState] = []
        self.current_view = ViewState(graph=build_overview_graph(self.full_graph), title="Tổng quan toàn hệ thống")
        self.current_selection: str | None = None
        self.node_positions: dict[str, tuple[float, float]] = {}
        self.node_sizes: dict[str, float] = {}

        self._build_layout()
        self._render_current_view()

    def _build_full_graph(self) -> nx.MultiDiGraph:
        print(f"[*] Building project graph from {self.repo_path}")
        graph = build_project_graph(self.repo_path)
        print(f"[+] Project graph ready: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph

    def _build_layout(self) -> None:
        self.topbar = ttk.Frame(self.root, padding=(12, 12, 12, 0))
        self.topbar.pack(side=tk.TOP, fill=tk.X)

        self.title_label = ttk.Label(self.topbar, text="Graph Viewer", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side=tk.LEFT)

        self.back_button = ttk.Button(self.topbar, text="Quay lại", command=self.go_back)
        self.back_button.pack(side=tk.LEFT, padx=(28, 0))

        self.expand_button = ttk.Button(self.topbar, text="Mở rộng thêm", command=self.expand_detail)
        self.expand_button.pack(side=tk.LEFT, padx=(10, 0))

        self.refresh_button = ttk.Button(self.topbar, text="Tải lại", command=self.reload_graph)
        self.refresh_button.pack(side=tk.RIGHT)

        self.container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.sidebar = ttk.Frame(self.container, padding=12)
        self.container.add(self.sidebar, weight=1)

        self.canvas_frame = ttk.Frame(self.container, padding=12)
        self.container.add(self.canvas_frame, weight=4)

        self._build_controls(self.sidebar)
        self._build_info_panel(self.sidebar)

        self.figure = plt.Figure(figsize=(12, 8), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.axis.set_axis_off()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.canvas_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.canvas_frame)
        self.toolbar.update()

        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)

    def _build_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.Labelframe(parent, text="Hiển thị", padding=10)
        controls.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(controls, text="Node types").pack(anchor=tk.W)
        for node_type in ["Module", "Class", "Function"]:
            ttk.Checkbutton(
                controls,
                text=node_type,
                variable=self.node_visibility[node_type],
                command=self._render_current_view,
            ).pack(anchor=tk.W)

        ttk.Separator(controls).pack(fill=tk.X, pady=8)
        ttk.Label(controls, text="Edge types").pack(anchor=tk.W)
        for edge_type in ["CALLS", "DEFINES", "CONTAINS", "IMPORTS", "INHERITS"]:
            ttk.Checkbutton(
                controls,
                text=edge_type,
                variable=self.edge_visibility[edge_type],
                command=self._render_current_view,
            ).pack(anchor=tk.W)

        ttk.Separator(controls).pack(fill=tk.X, pady=8)
        ttk.Label(
            controls,
            text="Mặc định viewer ưu tiên luồng chạy từ file khởi động, rồi đi xuống các hàm được gọi.",
            wraplength=360,
            foreground="#555555",
        ).pack(anchor=tk.W)

    def _build_info_panel(self, parent: ttk.Frame) -> None:
        info = ttk.Labelframe(parent, text="Thông tin node", padding=10)
        info.pack(fill=tk.BOTH, expand=True)

        self.info_name = ttk.Label(info, text="Tên: -", wraplength=360)
        self.info_name.pack(anchor=tk.W, pady=2)

        self.info_type = ttk.Label(info, text="Loại: -")
        self.info_type.pack(anchor=tk.W, pady=2)

        self.info_file = ttk.Label(info, text="File: -", wraplength=360)
        self.info_file.pack(anchor=tk.W, pady=2)

        self.info_id = ttk.Label(info, text="ID: -", wraplength=360)
        self.info_id.pack(anchor=tk.W, pady=2)

        self.summary_label = ttk.Label(info, text="Hướng dẫn sử dụng:")
        self.summary_label.pack(anchor=tk.W, pady=(10, 4))

        self.summary_text = ScrolledText(info, height=9, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=False)
        self.summary_text.configure(state="disabled")

        self.code_label = ttk.Label(info, text="Source code:")
        self.code_label.pack(anchor=tk.W, pady=(10, 4))

        self.code_text = ScrolledText(info, height=18, wrap=tk.NONE)
        self.code_text.pack(fill=tk.BOTH, expand=True)
        self.code_text.configure(state="disabled")

        self.hint_label = ttk.Label(
            info,
            text="Click node để xem mô tả, cách dùng và source code. Dùng bộ lọc bên trên để ẩn/hiện từng lớp graph.",
            wraplength=360,
            foreground="#555555",
        )
        self.hint_label.pack(anchor=tk.W, pady=(10, 0))

    def reload_graph(self) -> None:
        self.full_graph = self._build_full_graph()
        self.view_stack.clear()
        self.current_view = ViewState(graph=build_overview_graph(self.full_graph), title="Tổng quan toàn hệ thống")
        self.current_selection = None
        self._render_current_view()

    def expand_detail(self) -> None:
        if not self.current_view.focus_node_id:
            return

        self.view_stack.append(self.current_view)
        next_depth = self.current_view.detail_depth + 1 if self.current_view.detail_depth else 1
        focus_node_id = self.current_view.focus_node_id
        self.current_view = ViewState(
            graph=build_node_detail_graph(self.full_graph, focus_node_id, depth=next_depth),
            title=f"Chi tiết node: {self._node_label(focus_node_id, self.full_graph.nodes[focus_node_id])}",
            selected_node_id=focus_node_id,
            file_path=self.full_graph.nodes[focus_node_id].get("file_path"),
            focus_node_id=focus_node_id,
            detail_depth=next_depth,
        )
        self.current_selection = focus_node_id
        self._render_current_view()

    def go_back(self) -> None:
        if not self.view_stack:
            return
        self.current_view = self.view_stack.pop()
        self.current_selection = self.current_view.selected_node_id
        self._render_current_view()

    def _apply_filters(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        filtered = nx.MultiDiGraph()

        visible_nodes = {
            node_id
            for node_id, data in graph.nodes(data=True)
            if self.node_visibility.get(data.get("type", ""), tk.BooleanVar(value=True)).get()
        }

        for node_id in visible_nodes:
            filtered.add_node(node_id, **graph.nodes[node_id])

        for source_id, target_id, edge_data in graph.edges(data=True):
            if source_id not in visible_nodes or target_id not in visible_nodes:
                continue
            relationship = edge_data.get("relationship")
            if relationship and self.edge_visibility.get(relationship, tk.BooleanVar(value=True)).get():
                filtered.add_edge(source_id, target_id, **edge_data)

        return filtered

    def _render_current_view(self) -> None:
        graph = self._apply_filters(self.current_view.graph)

        self.title_label.configure(text=self.current_view.title)

        self.axis.clear()
        self.axis.set_axis_off()

        if not graph.nodes:
            self.axis.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
            self.canvas.draw_idle()
            self._update_info_panel(None)
            return

        if any("layer" in data for _, data in graph.nodes(data=True)):
            self.node_positions = layered_positions(graph)
        elif len(graph.nodes) <= 2:
            self.node_positions = nx.spring_layout(graph, seed=42, k=1.2)
        else:
            self.node_positions = nx.spring_layout(graph, seed=42, k=1.4 if len(graph.nodes) > 20 else 1.8)

        self.node_sizes = {}
        type_groups: dict[str, list[str]] = defaultdict(list)
        for node_id, data in graph.nodes(data=True):
            type_groups[data.get("type", "Unknown")].append(node_id)

        for node_type, node_ids in type_groups.items():
            sizes = []
            for node_id in node_ids:
                data = graph.nodes[node_id]
                if data.get("type") in {"Module", "File"}:
                    size = 5000
                elif data.get("type") == "Class":
                    size = 2100
                else:
                    size = 1600
                self.node_sizes[node_id] = size
                sizes.append(size)

            nx.draw_networkx_nodes(
                graph,
                self.node_positions,
                nodelist=node_ids,
                node_size=sizes,
                node_color=[NODE_COLORS.get(node_type, "#999999")] * len(node_ids),
                alpha=0.92,
                ax=self.axis,
            )

        edge_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for source_id, target_id, edge_data in graph.edges(data=True):
            edge_groups[edge_data.get("relationship", "OTHER")].append((source_id, target_id))

        for relationship, edges in edge_groups.items():
            style = EDGE_STYLES.get(relationship, {"color": "#cccccc", "style": "solid", "width": 0.8})
            nx.draw_networkx_edges(
                graph,
                self.node_positions,
                edgelist=edges,
                edge_color=style["color"],
                style=style["style"],
                width=style["width"],
                arrows=True,
                arrowsize=18,
                connectionstyle="arc3,rad=0.08",
                ax=self.axis,
            )

        labels = {node_id: self._node_label(node_id, data) for node_id, data in graph.nodes(data=True)}
        nx.draw_networkx_labels(
            graph,
            self.node_positions,
            labels=labels,
                font_size=7,
            font_weight="bold",
            font_family="sans-serif",
            ax=self.axis,
        )

        if self.current_selection in graph:
            x, y = self.node_positions[self.current_selection]
            highlight_size = self.node_sizes.get(self.current_selection, 1800) * 1.25
            self.axis.scatter(
                [x],
                [y],
                s=highlight_size,
                facecolors="none",
                edgecolors="#000000",
                linewidths=2.2,
                zorder=5,
            )

        self.axis.set_title(self.title_label.cget("text"), fontsize=15, pad=12)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self._update_info_panel(self.current_selection if self.current_selection in graph else None)

    def _node_label(self, node_id: str, data: dict[str, Any]) -> str:
        node_type = data.get("type", "")
        if node_type in {"Module", "File"}:
            return os.path.basename(data.get("file_path") or node_id)
        return data.get("name") or node_id.split("::")[-1]

    def _update_info_panel(self, node_id: str | None) -> None:
        source_graph = self.full_graph if node_id in self.full_graph else self.current_view.graph

        if not node_id or node_id not in source_graph:
            self.info_name.configure(text="Tên: -")
            self.info_type.configure(text="Loại: -")
            self.info_file.configure(text="File: -")
            self.info_id.configure(text="ID: -")
            self._set_text_widget(self.summary_text, "")
            self._set_text_widget(self.code_text, "")
            return

        data = source_graph.nodes[node_id]
        file_path = data.get("file_path") or "-"
        self.info_name.configure(text=f"Tên: {data.get('name', '-')}")
        self.info_type.configure(text=f"Loại: {data.get('type', '-')}")
        self.info_file.configure(text=f"File: {file_path}")
        self.info_id.configure(text=f"ID: {node_id}")

        summary = node_summary(self.full_graph, node_id)
        if data.get("type") == "Function":
            summary = f"{summary}\n\n{usage_hint(data)}"
        self._set_text_widget(self.summary_text, summary or "Không có mô tả.")
        self._set_text_widget(self.code_text, data.get("source_code", "") or "Không có source code.")

    def _set_text_widget(self, widget: ScrolledText, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value or "-")
        widget.configure(state="disabled")

    def _on_canvas_click(self, event: Any) -> None:
        if event.inaxes != self.axis:
            return

        node_id = self._find_node_at_position(event.xdata, event.ydata)
        if not node_id:
            return

        node_data = self.current_view.graph.nodes[node_id]
        focus_node_id = self._resolve_focus_node_id(node_id, node_data)
        if not focus_node_id:
            return

        self.view_stack.append(self.current_view)
        detail_depth = 1
        self.current_view = ViewState(
            graph=build_node_detail_graph(self.full_graph, focus_node_id, depth=detail_depth),
            title=f"Chi tiết node: {self._node_label(focus_node_id, self.full_graph.nodes[focus_node_id])}",
            selected_node_id=focus_node_id,
            file_path=self.full_graph.nodes[focus_node_id].get("file_path"),
            focus_node_id=focus_node_id,
            detail_depth=detail_depth,
        )
        self.current_selection = focus_node_id
        self._render_current_view()

    def _resolve_focus_node_id(self, node_id: str, node_data: dict[str, Any]) -> str | None:
        if node_id in self.full_graph:
            return node_id

        file_path = node_data.get("file_path")
        if not file_path:
            return None

        candidates = [
            candidate_id
            for candidate_id, data in self.full_graph.nodes(data=True)
            if data.get("file_path") == file_path
        ]
        if not candidates:
            return None

        for candidate_id in candidates:
            if self.full_graph.nodes[candidate_id].get("type") == "Module":
                return candidate_id
        return candidates[0]

    def _find_node_at_position(self, x: float | None, y: float | None) -> str | None:
        if x is None or y is None:
            return None

        best_node_id = None
        best_distance = float("inf")

        for node_id, (nx_pos, ny_pos) in self.node_positions.items():
            distance = ((x - nx_pos) ** 2 + (y - ny_pos) ** 2) ** 0.5
            threshold = 0.08 + (self.node_sizes.get(node_id, 1200) / 12000.0)
            if distance < threshold and distance < best_distance:
                best_node_id = node_id
                best_distance = distance

        return best_node_id

    def run(self) -> None:
        self.root.mainloop()


def launch_graph_viewer(repo_path: str) -> None:
    app = GraphViewerApp(repo_path)
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch the local desktop graph viewer")
    parser.add_argument("repo_path", nargs="?", default=".", help="Repository path to visualize")
    args = parser.parse_args()
    launch_graph_viewer(args.repo_path)