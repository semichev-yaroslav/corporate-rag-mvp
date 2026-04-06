from app.ingest.metadata_extraction import extract_document_metadata, normalize_counterparty


def test_extract_document_metadata_basic_fields() -> None:
    text = """
    Договор № 12-34/56 от 01.03.2026 заключен с ООО «Ромашка».
    Срок действия до 31.12.2026.
    Стоимость договора: 1 250 000 руб.
    """
    metadata = extract_document_metadata(text, "dogovor.docx")

    assert metadata.doc_type == "договор"
    assert metadata.counterparty_raw == "ООО «Ромашка»"
    assert metadata.counterparty_normalized == "ООО Ромашка"
    assert metadata.document_number == "12-34/56"
    assert str(metadata.end_date) == "2026-12-31"
    assert metadata.amount == "1 250 000"


def test_normalize_counterparty_removes_extra_spaces() -> None:
    assert normalize_counterparty('ООО   «Тест» ') == "ООО Тест"
