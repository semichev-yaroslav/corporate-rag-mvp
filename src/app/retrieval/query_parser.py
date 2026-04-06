from __future__ import annotations

import re

from app.ingest.metadata_extraction import NUMBER_PATTERN, normalize_counterparty, parse_ru_date
from app.schemas import ParsedQuery

COUNTERPARTY_PATTERN = re.compile(
    r"((?:ООО|АО|ПАО|ИП)\s+[\"«„“]?[A-Za-zА-Яа-я0-9 .,&-]+[\"»“”]?)"
)
DATE_PATTERN = re.compile(r"\b([0-3]?\d[./-][01]?\d[./-](?:19|20)\d{2})\b")


def parse_query(text: str) -> ParsedQuery:
    normalized_text = " ".join(text.lower().split())
    counterparty_match = COUNTERPARTY_PATTERN.search(text)
    document_number_match = NUMBER_PATTERN.search(text)
    date_match = DATE_PATTERN.search(text)

    question_type = "generic"
    if any(token in normalized_text for token in ("когда заканч", "срок", "до какого")):
        question_type = "end_date"
    elif any(token in normalized_text for token in ("сумм", "стоимост", "на какую сумму")):
        question_type = "amount"
    elif any(token in normalized_text for token in ("был ли", "есть ли", "заключен ли")):
        question_type = "existence"

    return ParsedQuery(
        original_text=text,
        normalized_text=normalized_text,
        question_type=question_type,
        counterparty=normalize_counterparty(counterparty_match.group(1)) if counterparty_match else None,
        document_number=document_number_match.group(1).strip() if document_number_match else None,
        date_hint=parse_ru_date(date_match.group(1)) if date_match else None,
    )
