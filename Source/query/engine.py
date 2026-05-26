import json
import os
import re
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
        self._name_to_node: dict[str, dict] = {}
        for node in self.nodes.values():
            self._name_to_node.setdefault(node["name"], node)

    # ── Stage 1: LLM node selection ──────────────────────────────────────────

    def _build_node_catalog(self) -> str:
        lines = []
        for node in self.nodes.values():
            filename = node["file_path"].split("/")[-1]
            lines.append(f"{node['name']} | {node['type']} | {filename}:{node['line_start']}")
        return "\n".join(lines)

    def _select_nodes_llm(self, question: str) -> tuple[list[dict], object]:
        """Call Haiku to pick relevant node names. Returns (nodes, usage)."""
        catalog = self._build_node_catalog()
        prompt = (
            f"Codebase nodes (name | type | file:line):\n{catalog}\n\n"
            f"Question: {question}\n\n"
            "Return a JSON array of the most relevant node names (max 8). "
            "Only use names that appear exactly in the list above. No explanation.\n"
            'Example: ["merge_project", "_node_dict", "GraphNode"]'
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if not match:
            return [], response.usage

        try:
            names = json.loads(match.group())
        except json.JSONDecodeError:
            return [], response.usage

        nodes = [self._name_to_node[n] for n in names if n in self._name_to_node]
        return nodes, response.usage

    def _find_nodes_keyword(self, question: str) -> list[dict]:
        """Fallback: keyword/word-boundary matching."""
        q_words = set(re.findall(r'[a-z]\w*', question.lower()))
        matched = []
        seen: set[str] = set()

        def add(node: dict):
            if node["id"] not in seen:
                matched.append(node)
                seen.add(node["id"])

        for node in self.nodes.values():
            name = node["name"].lower()
            if len(name) >= 4 and name in q_words:
                add(node)

        if not matched:
            long_q_words = {w for w in q_words if len(w) >= 5}
            for node in self.nodes.values():
                parts = set(re.findall(r'[a-z]+', re.sub(r'([A-Z])', r'_\1', node["name"]).lower()))
                parts = {p for p in parts if len(p) >= 5}
                if parts & long_q_words:
                    add(node)

        return matched[:8]

    def find_nodes(self, question: str) -> list[dict]:
        nodes, _ = self._select_nodes_llm(question)
        return nodes or self._find_nodes_keyword(question)

    # ── Context & answer ─────────────────────────────────────────────────────

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
                lines.append(f"  <- {edge['type']} {src['name']}")
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

    def ask_keyword_with_usage(self, question: str) -> dict:
        """Keyword-only retrieval + answer. Used by bench for baseline comparison."""
        nodes = self._find_nodes_keyword(question)
        context, sources = self.build_context(nodes)

        system = (
            "You are a code assistant. Answer questions about the codebase using the graph "
            "context below. Be concise. Reference specific names and file paths. "
            "If context is insufficient, say so.\n\n"
            f"=== GRAPH CONTEXT ===\n{context}\n===================="
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": question}],
        )

        return {
            "answer":    response.content[0].text,
            "sources":   sources,
            "s1_input":  0,
            "s1_output": 0,
            "s2_input":  response.usage.input_tokens,
            "s2_output": response.usage.output_tokens,
        }

    def ask_fullcode_with_usage(self, question: str, char_limit: int = 400_000) -> dict:
        """Send all source code directly — no retrieval. Baseline for token cost comparison.
        char_limit caps context size to stay under the 200k token limit (~4 chars/token)."""
        parts = [f"Project: {self.project}", ""]
        total_chars = 0
        truncated = False
        for node in self.nodes.values():
            if node.get("source_code"):
                chunk = f"[{node['type']}] {node['name']} — {node['file_path']}:{node['line_start']}\n"
                for line in node["source_code"].splitlines():
                    chunk += f"  {line}\n"
                chunk += "\n"
                if total_chars + len(chunk) > char_limit:
                    truncated = True
                    break
                parts.append(chunk)
                total_chars += len(chunk)
        if truncated:
            parts.append("... (source truncated to fit context limit)")
        context = "\n".join(parts)

        system = (
            "You are a code assistant. Answer questions about the codebase using the full source "
            "code context below. Be concise. Reference specific names and file paths. "
            "If context is insufficient, say so.\n\n"
            f"=== FULL SOURCE CODE ===\n{context}\n========================"
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": question}],
        )

        return {
            "answer":    response.content[0].text,
            "sources":   [],
            "s1_input":  0,
            "s1_output": 0,
            "s2_input":  response.usage.input_tokens,
            "s2_output": response.usage.output_tokens,
        }

    def ask_with_usage(self, question: str) -> dict:
        """Two-stage LLM retrieval + answer. Used by bench."""
        nodes, usage_s1 = self._select_nodes_llm(question)
        if not nodes:
            nodes = self._find_nodes_keyword(question)
            usage_s1 = None

        context, sources = self.build_context(nodes)

        system = (
            "You are a code assistant. Answer questions about the codebase using the graph "
            "context below. Be concise. Reference specific names and file paths. "
            "If context is insufficient, say so.\n\n"
            f"=== GRAPH CONTEXT ===\n{context}\n===================="
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": question}],
        )

        return {
            "answer": response.content[0].text,
            "sources": sources,
            "s1_input":  usage_s1.input_tokens  if usage_s1 else 0,
            "s1_output": usage_s1.output_tokens if usage_s1 else 0,
            "s2_input":  response.usage.input_tokens,
            "s2_output": response.usage.output_tokens,
        }
