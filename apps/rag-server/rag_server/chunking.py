"""Text chunking strategies.

Two modes:
1. `chunk_text`: plain character-based with overlap — for markdown, plans, generic docs.
2. `chunk_turns`: turn-based — for conversation logs (Claude sessions). Each user→assistant
   exchange is a "turn". Long turns get split with overlap. Short turns stay whole so the
   retrieval unit is a coherent conversation chunk, not a sentence fragment.

Sizes are tuned so Voyage's 1024-dim embeddings over Korean+English produce good recall
without costing too much. ~2000 chars ≈ 500 tokens, comfortably under voyage-3-large's
16k token limit with room for metadata.
"""
from __future__ import annotations

from dataclasses import dataclass

TARGET_CHARS = 2000
OVERLAP_CHARS = 200
MIN_CHARS = 50  # drop chunks shorter than this — usually noise


@dataclass
class Chunk:
    text: str
    metadata: dict  # e.g. {"turn_id": "...", "role": "assistant"}

    def __len__(self) -> int:
        return len(self.text)


def chunk_text(text: str, target: int = TARGET_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Character-based chunking with overlap. Drops trailing scraps smaller than MIN_CHARS."""
    text = text.strip()
    if len(text) <= target:
        return [text] if len(text) >= MIN_CHARS else []

    chunks: list[str] = []
    i = 0
    step = target - overlap
    while i < len(text):
        end = min(i + target, len(text))
        piece = text[i:end].strip()
        if len(piece) >= MIN_CHARS:
            chunks.append(piece)
        if end >= len(text):
            break
        i += step
    return chunks


@dataclass
class Turn:
    """One user message + its assistant reply (if any). Long turns get split further."""
    turn_id: str
    user_text: str
    assistant_text: str
    timestamp: str | None = None

    def render(self) -> str:
        parts = []
        if self.user_text:
            parts.append(f"User: {self.user_text}")
        if self.assistant_text:
            parts.append(f"Assistant: {self.assistant_text}")
        return "\n\n".join(parts)


def chunk_turns(turns: list[Turn]) -> list[Chunk]:
    """Turn-based chunking. Short turns kept whole; long turns split with overlap."""
    out: list[Chunk] = []
    for t in turns:
        rendered = t.render().strip()
        if len(rendered) < MIN_CHARS:
            continue
        if len(rendered) <= TARGET_CHARS:
            out.append(Chunk(text=rendered, metadata={"turn_id": t.turn_id, "timestamp": t.timestamp}))
        else:
            for i, piece in enumerate(chunk_text(rendered)):
                out.append(
                    Chunk(
                        text=piece,
                        metadata={
                            "turn_id": t.turn_id,
                            "timestamp": t.timestamp,
                            "sub_chunk": i,
                        },
                    )
                )
    return out
