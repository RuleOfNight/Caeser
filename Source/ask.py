"""
Interactive Q&A chat loop for paper markdown notes.
Usage: python ask.py <paper.md> path
"""

import sys
import re
import os
import json
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def parse_markdown(path: str) -> tuple[dict, dict[str, str]]:
    text = Path(path).read_text(encoding="utf-8")

    # Parse YAML
    meta = {}
    if text.startswith("---"):
        end = text.index("---", 3)
        frontmatter = text[3:end].strip()
        for line in frontmatter.splitlines():
            if ":" in line and not line.startswith(" ") and not line.startswith("-"):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        text = text[end + 3:].strip()

    # Split by ## headers
    sections: dict[str, str] = {}
    current_title = "intro"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_title] = "\n".join(current_lines).strip()

    return meta, sections


def build_system_prompt(meta: dict, sections: dict[str, str]) -> str:
    paper_title = meta.get("title", "Unknown Paper")
    authors = meta.get("authors", "")
    year = meta.get("year", "")

    paper_content = "\n\n".join(
        f"### {title}\n{content}"
        for title, content in sections.items()
        if content.strip()
    )

    return f"""Bạn là trợ lý nghiên cứu giúp người dùng hiểu sâu về paper học thuật.

Paper đang được thảo luận:
**{paper_title}** ({authors}, {year})

Các section trong paper (dùng tên chính xác khi trích dẫn): {", ".join(sections.keys())}

---
{paper_content}
---

Hướng dẫn:
- Trả lời dựa trên nội dung paper trên. Nếu paper không đề cập, hãy nói rõ và có thể bổ sung từ kiến thức chung.
- Trả lời bằng tiếng Việt trừ khi người dùng hỏi bằng tiếng Anh.
- Ngắn gọn, đúng trọng tâm. Dùng bullet point khi liệt kê.
- Nếu câu hỏi liên quan đến công thức hoặc code, trình bày rõ ràng.
- QUAN TRỌNG: Luôn trả lời theo định dạng JSON sau, không có text nào ngoài JSON:
{{
  "answer": "câu trả lời ở đây",
  "sources": [
    {{"section": "tên section", "quote": "đoạn trích ngắn liên quan nhất (tối đa 80 ký tự)"}}
  ]
}}"""


def chat(paper_path: str) -> None:
    if not ANTHROPIC_API_KEY:
        print("Cần set ANTHROPIC_API_KEY trong environment.")
        sys.exit(1)

    meta, sections = parse_markdown(paper_path)
    title = meta.get("title", Path(paper_path).stem)
    authors = meta.get("authors", "")
    year = meta.get("year", "")

    system = build_system_prompt(meta, sections)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    history: list[dict] = []

    print(f"\nPaper: {title}")
    if authors:
        print(f"Authors: {authors[:60]}{'...' if len(authors) > 60 else ''}")
    if year:
        print(f"Year: {year}")
    print(f"Sections: {', '.join(sections.keys())}")
    print("\nGõ câu hỏi về paper. 'exit' để thoát, 'clear' để reset lịch sử.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Bye.")
            break
        if user_input.lower() == "clear":
            history.clear()
            print("[Lịch sử đã được reset]\n")
            continue

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=history,
        )

        raw = response.content[0].text.strip()
        history.append({"role": "assistant", "content": raw})

        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = json.loads(match.group()) if match else None
        except (json.JSONDecodeError, AttributeError):
            parsed = None

        if parsed and "answer" in parsed:
            print(f"\nAssistant: {parsed['answer']}")
            sources = parsed.get("sources") or []
            if sources:
                print("\n  Nguồn:")
                for s in sources:
                    section = s.get("section", "?")
                    quote = s.get("quote", "").strip()
                    print(f"  [{section}] \"{quote}\"")
            print()
        else:
            print(f"\nAssistant: {raw}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask.py <paper.md>")
        sys.exit(1)
    chat(sys.argv[1])
