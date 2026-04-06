from app.retrieval.query_parser import parse_query


def test_parse_query_detects_counterparty_and_question_type() -> None:
    parsed = parse_query("Когда заканчивается договор с ООО Ромашка?")

    assert parsed.question_type == "end_date"
    assert parsed.counterparty == "ООО Ромашка"
