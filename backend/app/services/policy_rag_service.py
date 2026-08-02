from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class PolicyChunk:
    chunk_id: str
    doc: str
    section: str
    text: str


class PolicyRAGService:
    """
    Lightweight local-file RAG (no vector DB, no embeddings).
    - Loads markdown files under repo_root/policies/*.md
    - Splits by headings (#, ##, ###)
    - Keyword-scores chunks and returns topK
    """

    def __init__(self, policies_dir: str | None = None):
        this_file = Path(__file__).resolve()

        # Find repo root by walking upward until we find a "policies" directory
        repo_root = None
        for p in this_file.parents:
            if (p / "policies").exists():
                repo_root = p
                break

        # Fallback: assume structure .../risk-platform-demo/backend/app/services/this_file
        if repo_root is None:
            repo_root = this_file.parents[3]  # best-effort

        self.policies_dir = Path(policies_dir) if policies_dir else (repo_root / "policies")
        self._chunks: List[PolicyChunk] = []

    def load(self) -> None:
        if not self.policies_dir.exists():
            self._chunks = []
            return

        chunks: List[PolicyChunk] = []
        for p in sorted(self.policies_dir.glob("*.md")):
            doc = p.name
            md = p.read_text(encoding="utf-8", errors="ignore")
            chunks.extend(self._split_markdown(doc, md))

        self._chunks = chunks

    def search(self, query: str, top_k: int = 5) -> List[PolicyChunk]:
        if not self._chunks:
            self.load()

        q_tokens = self._tokenize(query)
        scored: List[Tuple[float, PolicyChunk]] = []
        for ch in self._chunks:
            score = self._score(q_tokens, ch.text)
            if score > 0:
                scored.append((score, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    # -------- internal helpers --------

    def _split_markdown(self, doc: str, md: str) -> List[PolicyChunk]:
        lines = md.splitlines()
        chunks: List[PolicyChunk] = []

        heading_stack: List[str] = []
        buf: List[str] = []

        def flush():
            nonlocal buf
            content = "\n".join(buf).strip()
            if content:
                section = " / ".join(heading_stack) if heading_stack else "ROOT"
                safe_section = re.sub(r"[^a-zA-Z0-9]+", "_", section).strip("_")
                idx = len([c for c in chunks if c.doc == doc and c.section == section]) + 1
                chunk_id = f"{doc}#{safe_section}#{idx:03d}"
                chunks.append(
                    PolicyChunk(
                        chunk_id=chunk_id,
                        doc=doc,
                        section=section,
                        text=content,
                    )
                )
            buf = []

        for line in lines:
            m = re.match(r"^(#{1,3})\s+(.*)$", line)
            if m:
                flush()
                level = len(m.group(1))
                title = m.group(2).strip()

                if level == 1:
                    heading_stack = [title]
                elif level == 2:
                    heading_stack = heading_stack[:1] + [title] if heading_stack else [title]
                else:  # level == 3
                    if len(heading_stack) >= 2:
                        heading_stack = heading_stack[:2] + [title]
                    else:
                        heading_stack = heading_stack + [title]
                continue

            buf.append(line)

        flush()
        return chunks

    def _tokenize(self, s: str) -> List[str]:
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return [t for t in s.split() if len(t) >= 3]

    def _score(self, q_tokens: List[str], text: str) -> float:
        t = text.lower()
        score = 0.0
        for tok in q_tokens:
            cnt = t.count(tok)
            if cnt:
                score += 1.0 + 0.2 * min(cnt, 10)
        return score