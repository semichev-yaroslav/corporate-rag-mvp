from __future__ import annotations

import re
from datetime import date

from app.schemas import DocumentMetadataPayload

COUNTERPARTY_PATTERN = re.compile(
    r"((?:ООО|АО|ПАО|ИП)\s+[\"«„“]?[A-Za-zА-Яа-я0-9 .,&-]+[\"»“”]?)"
)
NUMBER_PATTERN = re.compile(
    r"(?:договор(?:а)?|контракт(?:а)?|соглашени(?:е|я))\s*(?:№|N)\s*([A-Za-zА-Яа-я0-9/-]+)",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"\b([0-3]?\d[./-][01]?\d[./-](?:19|20)\d{2})\b")
AMOUNT_PATTERN = re.compile(
    r"(?:на сумму|сумма(?: договора)?|стоимость(?: договора)?)\s*[:-]?\s*([\d\s]+(?:[.,]\d{1,2})?)\s*(руб(?:\.|лей|ля)?|RUB|USD|EUR|€|\$)?",
    re.IGNORECASE,
)
END_DATE_PATTERN = re.compile(
    r"(?:действует до|срок(?: действия)? до|оканчивается|дата окончания)\s*[:-]?\s*([0-3]?\d[./-][01]?\d[./-](?:19|20)\d{2})",
    re.IGNORECASE,
)
START_DATE_PATTERN = re.compile(
    r"(?:действует с|начало действия|вступает в силу)\s*[:-]?\s*([0-3]?\d[./-][01]?\d[./-](?:19|20)\d{2})",
    re.IGNORECASE,
)


def normalize_counterparty(value: str | None) -> str | None:
    if not value:
        return None
    normalized = (
        value.replace("«", " ")
        .replace("»", " ")
        .replace("„", " ")
        .replace("“", " ")
        .replace("”", " ")
        .replace('"', " ")
    )
    normalized = " ".join(normalized.split())
    return normalized.strip(" ,;")


def parse_ru_date(value: str | None) -> date | None:
    if not value:
        return None
    clean = value.replace("-", ".").replace("/", ".")
    day, month, year = clean.split(".")
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def detect_doc_type(file_name: str, text: str) -> str | None:
    lowered = f"{file_name.lower()} {text.lower()[:1000]}"
    if "дополнительное соглашение" in lowered:
        return "дополнительное соглашение"
    if "договор" in lowered or "контракт" in lowered:
        return "договор"
    if "счет" in lowered:
        return "счет"
    if "акт" in lowered:
        return "акт"
    return None


def extract_document_metadata(text: str, file_name: str) -> DocumentMetadataPayload:
    counterparty_match = COUNTERPARTY_PATTERN.search(text)
    document_number_match = NUMBER_PATTERN.search(text)
    amount_match = AMOUNT_PATTERN.search(text)
    end_date_match = END_DATE_PATTERN.search(text)
    start_date_match = START_DATE_PATTERN.search(text)
    all_dates = DATE_PATTERN.findall(text)

    counterparty_raw = counterparty_match.group(1).strip() if counterparty_match else None
    currency = None
    amount = None
    if amount_match:
        amount = " ".join(amount_match.group(1).split())
        currency = amount_match.group(2)
        if currency:
            currency = currency.upper().replace("РУБ", "RUB").replace("РУБ.", "RUB")

    return DocumentMetadataPayload(
        doc_type=detect_doc_type(file_name, text),
        counterparty_raw=counterparty_raw,
        counterparty_normalized=normalize_counterparty(counterparty_raw),
        document_number=document_number_match.group(1).strip() if document_number_match else None,
        document_date=parse_ru_date(all_dates[0]) if all_dates else None,
        start_date=parse_ru_date(start_date_match.group(1)) if start_date_match else None,
        end_date=parse_ru_date(end_date_match.group(1)) if end_date_match else None,
        amount=amount,
        currency=currency,
    )
