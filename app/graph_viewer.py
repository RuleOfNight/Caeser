from __future__ import annotations

import os
import tkinter as tk
from collections import defaultdict
from dataclasses import dataclass
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from parsing.parser import parse_file
from extraction.extractor import extract
from graph.builder import build_graph
from ingestion.file_scanner import scan_py_files


@dataclass
class ViewState:
    graph: nx.MultiDiGraph
    title: str
    selected_node_id: str | None = None
    file_path: str | None = None


def _node_type_to_color(node_type: str) -> str:
    color_map = {
        "File": "#1f77b4",
        "Class": "#2ca02c",
        "Function": "#d62728",
        "Variable": "#bcbd22",
        "Dependency": "#7f7f7f",
    }
    return color_map.get(node_type, "#999999")


def _node_label(node_id: str, data: dict[str, Any]) -> str:
    node_type = data.get("type", "")
    if node_type == "File":
        return os.path.basename(data.get("file_path") or node_id)
    return data.get("name") or node_id.split("::")[-1]


def _safe_basename(path: str) -> str:
    return path.replace("\\", "/").split("/")[-1]


def build_file_level_graph(full_graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Collapse the full graph into a file-to-file overview graph."""
    file_graph = nx.MultiDiGraph()
    file_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"node_count": 0, "function_count": 0, "class_count": 0, "dependency_count": 0}
    )

    for node_id, data in full_graph.nodes(data=True):
        file_path = data.get("file_path")
        if not file_path:
            continue

        stats = file_stats[file_path]
        stats["node_count"] += 1

        node_type = data.get("type")
        if node_type == "Function":
            stats["function_count"] += 1
        elif node_type == "Class":
            stats["class_count"] += 1
        elif node_type == "Dependency":
            stats["dependency_count"] += 1

    for file_path, stats in file_stats.items():
        label = _safe_basename(file_path)
        file_graph.add_node(
            file_path,
            name=label,
            type="File",
            file_path=file_path,
            stats=stats,
            display_title=f"{label}\n({stats['node_count']} nodes)",
            size=3600 + stats["node_count"] * 150,
        )

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for source_id, target_id, edge_data in full_graph.edges(data=True):
        if edge_data.get("relationship") != "CALLS":
            continue

        source_file = full_graph.nodes[source_id].get("file_path")
        target_file = full_graph.nodes[target_id].get("file_path")
        if not source_file or not target_file or source_file == target_file:
            continue

        edge_weights[(source_file, target_file)] += 1

    for (source_file, target_file), weight in edge_weights.items():
        file_graph.add_edge(source_file, target_file, relationship="CALLS", weight=weight)

    return file_graph


def build_file_detail_graph(full_graph: nx.MultiDiGraph, file_path: str, depth: int = 1) -> nx.MultiDiGraph:
    """Build a focused graph for a single file and its immediate relations."""
    detail_graph = nx.MultiDiGraph()

    file_nodes = {
        node_id
        for node_id, data in full_graph.nodes(data=True)
        if data.get("file_path") == file_path
    }

    if not file_nodes:
        return detail_graph

    file_node_id = next(
        (
            node_id
            for node_id, data in full_graph.nodes(data=True)
            if data.get("type") == "File" and data.get("file_path") == file_path
        ),
        None,
    )

    included_nodes = set(file_nodes)
    if file_node_id:
        included_nodes.add(file_node_id)

    frontier = set(file_nodes)
    for _ in range(max(depth, 0)):
        next_frontier = set()
        for node_id in frontier:
            neighbors = set(full_graph.predecessors(node_id)) | set(full_graph.successors(node_id))
            for neighbor in neighbors:
                edge_data_map = full_graph.get_edge_data(node_id, neighbor) or full_graph.get_edge_data(neighbor, node_id) or {}
                relationship_types = {data.get("relationship") for data in edge_data_map.values()}

                if relationship_types & {"CALLS", "CONTAINS", "INHERITS", "IMPORTS", "USES_VARIABLE"}:
                    if neighbor not in included_nodes:
                        next_frontier.add(neighbor)
                    included_nodes.add(neighbor)

        frontier = next_frontier

    for node_id in included_nodes:
        detail_graph.add_node(node_id, **full_graph.nodes[node_id])

    for source_id, target_id, edge_data in full_graph.edges(data=True):
        if source_id in included_nodes and target_id in included_nodes:
            detail_graph.add_edge(source_id, target_id, **edge_data)

    return detail_graph


class GraphViewerApp:
    """Desktop graph viewer with clickable nodes and a collapsible info panel."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.root = tk.Tk()
        self.root.title("CAESER Graph Viewer")
        self.root.geometry("1500x950")

        self.full_graph = self._build_full_graph(repo_path)
        self.file_graph = build_file_level_graph(self.full_graph)

        self.view_stack: list[ViewState] = []
        self.current_view = ViewState(graph=self.file_graph, title="Tổng quan theo file")
        self.node_positions: dict[str, tuple[float, float]] = {}
        self.node_sizes: dict[str, float] = {}
        self.current_selection: str | None = None
        self.panel_visible = True

        self._build_layout()
        self._render_current_view()

    def _build_full_graph(self, repo_path: str) -> nx.MultiDiGraph:
        print(f"[*] Building interactive graph from {os.path.abspath(repo_path)}")
        files = scan_py_files(repo_path)

        modules = []
        for file_path in files:
            try:
                tree = parse_file(file_path)
                modules.append(extract(tree, file_path))
            except (SyntaxError, Exception):
                pass

        dg = build_graph(modules)

        # Convert DiGraph to MultiDiGraph with attributes expected by the viewer
        mg = nx.MultiDiGraph()
        for node_id, data in dg.nodes(data=True):
            mg.add_node(
                node_id,
                name=data.get("name", node_id.split("::")[-1]),
                type="Function",
                file_path=data.get("file", ""),
                content="",
                source_code="",
            )
        for u, v in dg.edges():
            mg.add_edge(u, v, relationship="CALLS")

        print(f"[+] Interactive graph ready: {len(mg.nodes)} nodes, {len(mg.edges)} edges")
        return mg

    def _build_layout(self) -> None:
        self.topbar = ttk.Frame(self.root, padding=(10, 10, 10, 0))
        self.topbar.pack(side=tk.TOP, fill=tk.X)

        self.title_label = ttk.Label(self.topbar, text="Tổng quan theo file", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side=tk.LEFT)

        self.toggle_button = ttk.Button(self.topbar, text="Ẩn bảng thông tin", command=self.toggle_info_panel)
        self.toggle_button.pack(side=tk.RIGHT)

        self.back_button = ttk.Button(self.topbar, text="Quay lại", command=self.go_back)
        self.back_button.pack(side=tk.RIGHT, padx=(0, 10))

        self.container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.info_frame = ttk.Frame(self.container, padding=12)
        self._build_info_panel(self.info_frame)
        self.container.add(self.info_frame, weight=1)

        self.canvas_frame = ttk.Frame(self.container, padding=12)
        self.container.add(self.canvas_frame, weight=4)

        self.figure = plt.Figure(figsize=(12, 8), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.axis.set_axis_off()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.canvas_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.canvas_frame)
        self.toolbar.update()

        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)

    def _build_info_panel(self, parent: ttk.Frame) -> None:
        header = ttk.Label(parent, text="Thông tin node", font=("Segoe UI", 13, "bold"))
        header.pack(anchor=tk.W, pady=(0, 10))

        self.info_name = ttk.Label(parent, text="Tên: -", wraplength=340)
        self.info_name.pack(anchor=tk.W, pady=2)

        self.info_type = ttk.Label(parent, text="Loại: -")
        self.info_type.pack(anchor=tk.W, pady=2)

        self.info_file = ttk.Label(parent, text="File: -", wraplength=340)
        self.info_file.pack(anchor=tk.W, pady=2)

        self.info_id = ttk.Label(parent, text="ID: -", wraplength=340)
        self.info_id.pack(anchor=tk.W, pady=2)

        self.summary_label = ttk.Label(parent, text="Mô tả:")
        self.summary_label.pack(anchor=tk.W, pady=(10, 4))

        self.summary_text = ScrolledText(parent, height=8, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=False)
        self.summary_text.configure(state="disabled")

        self.code_label = ttk.Label(parent, text="Source code:")
        self.code_label.pack(anchor=tk.W, pady=(10, 4))

        self.code_text = ScrolledText(parent, height=18, wrap=tk.NONE)
        self.code_text.pack(fill=tk.BOTH, expand=True)
        self.code_text.configure(state="disabled")

        self.hint_label = ttk.Label(
            parent,
            text="Click a file node to drill down. Click any node to inspect its details.",
            foreground="#555555",
            wraplength=340,
        )
        self.hint_label.pack(anchor=tk.W, pady=(10, 0))

    def _set_text_widget(self, widget: ScrolledText, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value or "-")
        widget.configure(state="disabled")

    def _update_info_panel(self, node_id: str | None) -> None:
        if not node_id or node_id not in self.current_view.graph:
            self.info_name.configure(text="Tên: -")
            self.info_type.configure(text="Loại: -")
            self.info_file.configure(text="File: -")
            self.info_id.configure(text="ID: -")
            self._set_text_widget(self.summary_text, "")
            self._set_text_widget(self.code_text, "")
            return

        data = self.current_view.graph.nodes[node_id]
        file_path = data.get("file_path") or "-"
        content = data.get("content", "")
        source_code = data.get("source_code", "")

        self.info_name.configure(text=f"Tên: {data.get('name', '-')}")
        self.info_type.configure(text=f"Loại: {data.get('type', '-')}")
        self.info_file.configure(text=f"File: {file_path}")
        self.info_id.configure(text=f"ID: {node_id}")
        self._set_text_widget(self.summary_text, content or "Không có mô tả.")
        self._set_text_widget(self.code_text, source_code or "Không có source code.")

    def toggle_info_panel(self) -> None:
        if self.panel_visible:
            self.container.forget(self.info_frame)
            self.toggle_button.configure(text="Hiện bảng thông tin")
        else:
            self.container.insert(0, self.info_frame, weight=1)
            self.toggle_button.configure(text="Ẩn bảng thông tin")
        self.panel_visible = not self.panel_visible

    def go_back(self) -> None:
        if not self.view_stack:
            return

        previous = self.view_stack.pop()
        self.current_view = previous
        self.current_selection = previous.selected_node_id
        self._render_current_view()

    def _render_current_view(self) -> None:
        graph = self.current_view.graph
        self.title_label.configure(text=self.current_view.title)
        self.axis.clear()
        self.axis.set_axis_off()

        if len(graph.nodes) == 0:
            self.axis.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
            self.canvas.draw_idle()
            self._update_info_panel(None)
            return

        self.node_positions = nx.spring_layout(graph, seed=42, k=0.9 if len(graph.nodes) > 20 else 1.2)
        self.node_sizes = {}

        type_groups: dict[str, list[str]] = defaultdict(list)
        for node_id, data in graph.nodes(data=True):
            type_groups[data.get("type", "Unknown")].append(node_id)

        for node_type, node_ids in type_groups.items():
            sizes = []
            for node_id in node_ids:
                data = graph.nodes[node_id]
                if data.get("type") == "File":
                    size = data.get("size", 3600)
                elif data.get("type") == "Function":
                    size = 1500
                elif data.get("type") == "Class":
                    size = 1700
                else:
                    size = 1100
                self.node_sizes[node_id] = size
                sizes.append(size)

            nx.draw_networkx_nodes(
                graph,
                self.node_positions,
                nodelist=node_ids,
                node_size=sizes,
                node_color=[_node_type_to_color(node_type)] * len(node_ids),
                alpha=0.92,
                ax=self.axis,
            )

        edge_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for source_id, target_id, edge_data in graph.edges(data=True):
            edge_groups[edge_data.get("relationship", "OTHER")].append((source_id, target_id))

        edge_styles = {
            "CALLS": {"color": "#ff9896", "style": "solid", "width": 1.8},
            "CONTAINS": {"color": "#aec7e8", "style": "dashed", "width": 1.0},
            "INHERITS": {"color": "#98df8a", "style": "solid", "width": 1.4},
            "IMPORTS": {"color": "#c5b0d5", "style": "dotted", "width": 1.0},
            "USES_VARIABLE": {"color": "#ffbb78", "style": "dotted", "width": 1.0},
        }

        for relationship, edges in edge_groups.items():
            style = edge_styles.get(relationship, {"color": "#cccccc", "style": "solid", "width": 0.8})
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

        labels = {node_id: _node_label(node_id, data) for node_id, data in graph.nodes(data=True)}
        nx.draw_networkx_labels(
            graph,
            self.node_positions,
            labels=labels,
            font_size=8,
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

        self.axis.set_title(self.current_view.title, fontsize=16, pad=12)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self._update_info_panel(self.current_selection)

    def _on_canvas_click(self, event: Any) -> None:
        if event.inaxes != self.axis:
            return

        node_id = self._find_node_at_position(event.xdata, event.ydata)
        if not node_id:
            return

        self.current_selection = node_id
        self._update_info_panel(node_id)

        node_data = self.current_view.graph.nodes[node_id]
        if node_data.get("type") == "File" and self.current_view.file_path != node_data.get("file_path"):
            self._drill_into_file(node_data.get("file_path", ""), selected_node_id=node_id)
        else:
            self._render_current_view()

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

    def _drill_into_file(self, file_path: str, selected_node_id: str | None = None) -> None:
        if not file_path:
            return

        detail_graph = build_file_detail_graph(self.full_graph, file_path=file_path, depth=1)
        if len(detail_graph.nodes) == 0:
            return

        self.view_stack.append(self.current_view)
        file_name = _safe_basename(file_path)
        self.current_view = ViewState(
            graph=detail_graph,
            title=f"Chi tiết file: {file_name}",
            selected_node_id=selected_node_id,
            file_path=file_path,
        )
        self.current_selection = selected_node_id
        self._render_current_view()

    def run(self) -> None:
        self.root.mainloop()


def launch_graph_viewer(repo_path: str) -> None:
    """Launch the local desktop graph viewer."""
    app = GraphViewerApp(repo_path)
    app.run()
