from app.ingest.chunking import build_chunks
from app.schemas import DocumentFragment, ParsedDocument


def test_build_chunks_preserves_page_ranges() -> None:
    parsed_document = ParsedDocument(
        file_path="contract.pdf",
        file_name="contract.pdf",
        file_type="pdf",
        fragments=[
            DocumentFragment(text="слово " * 450, page_from=1, page_to=1, order=1),
            DocumentFragment(text="слово " * 450, page_from=2, page_to=2, order=2),
            DocumentFragment(text="слово " * 450, page_from=3, page_to=3, order=3),
        ],
    )

    chunks = build_chunks(parsed_document, target_tokens=1000, overlap_tokens=120)

    assert len(chunks) >= 2
    assert chunks[0].page_from == 1
    assert chunks[0].page_to >= 2
