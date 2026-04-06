from __future__ import annotations

from pathlib import Path

import fitz

from app.schemas import DocumentFragment, ParsedDocument


def parse_pdf(file_path: str) -> ParsedDocument:
    pdf = fitz.open(file_path)
    fragments: list[DocumentFragment] = []
    try:
        for page_index, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            fragments.append(
                DocumentFragment(
                    text=text,
                    page_from=page_index,
                    page_to=page_index,
                    section_title=None,
                    order=page_index,
                )
            )
    finally:
        pdf.close()

    return ParsedDocument(
        file_path=str(Path(file_path).resolve()),
        file_name=Path(file_path).name,
        file_type="pdf",
        fragments=fragments,
    )
