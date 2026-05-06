import json
import os
from pathlib import Path

import anthropic


class QueryEngine:
    def __init__(self, graph_path: str):
        data = json.loads(Path(graph_path).read_text(encoding="utf-8"))
        self.project = data["project"]
        self.nodes: dict[str, dict] = {n["id"]: n for n in data["nodes"]}

        self.outgoing: dict[str, list[dict]] = {nid: [] for nid in self.nodes}
        self.incoming: dict[str, list[dict]] = {nid: [] for nid in self.nodes}
        for edge in data["edges"]:
            if edge["confidence"] > 0.0:
                src, tgt = edge["source_id"], edge["target_id"]
                if src in self.outgoing:
                    self.outgoing[src].append(edge)
                if tgt in self.incoming:
                    self.incoming[tgt].append(edge)

        self._client = anthropic.Anthropic()

    def find_nodes(self, question: str) -> list[dict]:
        q = question.lower()
        matched = []
        seen: set[str] = set()

        for node in self.nodes.values():
            if node["name"].lower() in q and node["id"] not in seen:
                matched.append(node)
                seen.add(node["id"])

        if not matched:
            for node in self.nodes.values():
                name = node["name"].lower()
                if any(name in word or word in name for word in q.split() if len(word) > 3):
                    if node["id"] not in seen:
                        matched.append(node)
                        seen.add(node["id"])

        return matched[:8]

    def _node_summary(self, node: dict) -> str:
        lines = [f"[{node['type']}] {node['name']} — {node['file_path']}:{node['line_start']}"]
        if node.get("docstring"):
            lines.append(f"  doc: {node['docstring'][:120]}")
        if node.get("source_code"):
            code = node["source_code"]
            if len(code) > 1500:
                code = code[:1500] + "\n  ... (truncated)"
            lines.append("  source:")
            for line in code.splitlines():
                lines.append(f"    {line}")
        for edge in self.outgoing.get(node["id"], []):
            tgt = self.nodes.get(edge["target_id"])
            if tgt:
                lines.append(f"  {edge['type']} → {tgt['name']}")
        for edge in self.incoming.get(node["id"], []):
            src = self.nodes.get(edge["source_id"])
            if src:
                lines.append(f"  ← {edge['type']} {src['name']}")
        return "\n".join(lines)

    def build_context(self, nodes: list[dict]) -> tuple[str, list[str]]:
        if not nodes:
            modules = [n for n in self.nodes.values() if n["type"] == "Module"][:15]
            ctx = f"Project: {self.project}\nModules: {', '.join(m['name'] for m in modules)}"
            return ctx, []

        parts = [f"Project: {self.project}", ""]
        names_used = []
        for node in nodes:
            parts.append(self._node_summary(node))
            parts.append("")
            names_used.append(node["name"])
        return "\n".join(parts), names_used

    def ask(self, question: str, history: list[dict]) -> tuple[str, list[str]]:
        matched = self.find_nodes(question)
        context, sources = self.build_context(matched)

        system = (
            "You are a code assistant. Answer questions about the codebase using the graph "
            "context below. Be concise. Reference specific names and file paths. "
            "If context is insufficient, say so.\n\n"
            f"=== GRAPH CONTEXT ===\n{context}\n===================="
        )

        messages = history + [{"role": "user", "content": question}]

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=messages,
        )

        return response.content[0].text, sources
