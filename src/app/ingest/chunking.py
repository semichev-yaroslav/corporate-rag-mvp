from __future__ import annotations

from app.schemas import ChunkPayload, DocumentFragment, ParsedDocument


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.15))


def _split_oversized_fragment(fragment: DocumentFragment, max_tokens: int) -> list[DocumentFragment]:
    if estimate_tokens(fragment.text) <= max_tokens:
        return [fragment]

    words = fragment.text.split()
    chunks: list[DocumentFragment] = []
    step = max(50, int(max_tokens * 0.8))
    start = 0
    order = fragment.order
    while start < len(words):
        end = min(len(words), start + step)
        chunks.append(
            DocumentFragment(
                text=" ".join(words[start:end]),
                page_from=fragment.page_from,
                page_to=fragment.page_to,
                section_title=fragment.section_title,
                order=order,
            )
        )
        start = end
        order += 1
    return chunks


def build_chunks(
    parsed_document: ParsedDocument,
    target_tokens: int = 1000,
    overlap_tokens: int = 150,
) -> list[ChunkPayload]:
    expanded_fragments: list[DocumentFragment] = []
    for fragment in parsed_document.fragments:
        expanded_fragments.extend(_split_oversized_fragment(fragment, target_tokens))

    chunks: list[ChunkPayload] = []
    current: list[DocumentFragment] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        text = "\n\n".join(fragment.text for fragment in current if fragment.text.strip()).strip()
        if not text:
            current = []
            current_tokens = 0
            return
        pages = [fragment.page_from for fragment in current if fragment.page_from is not None]
        page_tos = [fragment.page_to for fragment in current if fragment.page_to is not None]
        section_title = next(
            (fragment.section_title for fragment in reversed(current) if fragment.section_title),
            None,
        )
        chunks.append(
            ChunkPayload(
                chunk_index=len(chunks),
                text=text,
                page_from=min(pages) if pages else None,
                page_to=max(page_tos) if page_tos else None,
                section_title=section_title,
                token_count=estimate_tokens(text),
            )
        )
        overlap: list[DocumentFragment] = []
        overlap_count = 0
        for fragment in reversed(current):
            overlap.insert(0, fragment)
            overlap_count += estimate_tokens(fragment.text)
            if overlap_count >= overlap_tokens:
                break
        current = overlap
        current_tokens = sum(estimate_tokens(fragment.text) for fragment in current)

    for fragment in expanded_fragments:
        fragment_tokens = estimate_tokens(fragment.text)
        if current and current_tokens + fragment_tokens > target_tokens and current_tokens >= 800:
            flush()
        current.append(fragment)
        current_tokens += fragment_tokens

    flush()
    return chunks
