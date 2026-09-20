"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document

# Splits before "--- reply N (X votes) ---" without consuming it.
REPLY_MARKER = re.compile(r"(?=^--- reply )", re.M)


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    One chunk per reply, with the thread question prepended to each.

    The advice_threads documents are short forum threads that already carry
    their own structure: a `THREAD:` line, then replies marked
    `--- reply N (X votes) ---`. Each reply is one person giving one piece of
    advice, so a reply is the natural unit to retrieve.

    Cutting on those markers instead of on a character count means no chunk
    ever ends mid-sentence. The thread question is repeated at the top of every
    chunk so that a reply like "depends whether your building has a kitchen"
    still embeds near the topic it is answering, instead of floating free of
    the question that gave it meaning.

    A document with no reply markers stays one chunk.
    """
    chunks: list[Chunk] = []
    for doc in documents:
        if not doc.text.strip():
            continue

        # Split before each reply marker, keeping the marker with its reply.
        parts = [p.strip() for p in REPLY_MARKER.split(doc.text) if p.strip()]

        # Anything before the first marker is the thread question. If the
        # document has no markers at all, there is nothing to split.
        if parts and not parts[0].startswith("--- reply"):
            header, replies = parts[0], parts[1:]
        else:
            header, replies = "", parts

        if not replies:
            replies = [header] if header else []
            header = ""

        for index, reply in enumerate(replies):
            text = f"{header}\n\n{reply}" if header else reply
            chunks.append(
                Chunk(
                    text=text,
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks

    # Earlier strategies, kept so it is easy to switch back and compare:
    # return split_into_thirds(documents)
    # return fallback_split(documents)


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
