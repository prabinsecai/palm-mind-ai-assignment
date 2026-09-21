import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    index: int
    text: str

def fixed_chunks(text: str, size: int = 1000, overlap: int = 150) -> list[Chunk]:
    if size <= overlap: raise ValueError("chunk size must be greater than overlap")
    chunks=[]; start=0; idx=0
    while start < len(text):
        piece=text[start:start+size].strip()
        if piece: chunks.append(Chunk(idx,piece)); idx += 1
        start += size-overlap
    return chunks

def recursive_chunks(text: str, size: int = 1000, overlap: int = 150) -> list[Chunk]:
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    raw=[]; current=""
    for p in paragraphs:
        if len(p) <= size and len(current)+len(p)+2 <= size:
            current = f"{current}\n\n{p}".strip()
        else:
            if current: raw.append(current)
            if len(p) <= size: current=p
            else:
                raw.extend([c.text for c in fixed_chunks(p,size,overlap)])
                current=""
    if current: raw.append(current)
    # apply overlap between semantic chunks while retaining boundaries
    out=[]
    for i, item in enumerate(raw):
        if i and overlap:
            prefix=raw[i-1][-overlap:]
            item=f"{prefix}\n{item}"[:size]
        out.append(Chunk(i,item.strip()))
    return out

def make_chunks(text: str, strategy: str) -> list[Chunk]:
    return fixed_chunks(text) if strategy == "fixed" else recursive_chunks(text)
