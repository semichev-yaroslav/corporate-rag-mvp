from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import get_settings


def load_cases(fixture_path: Path) -> list[dict]:
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def answer_matches(case: dict, payload: dict) -> tuple[bool, list[str]]:
    answer = payload["answer"].lower()
    reasons: list[str] = []

    if case.get("expected_to_find", True):
        if not payload.get("citations"):
            reasons.append("нет источников")
        for token in case.get("must_include", []):
            if token.lower() not in answer:
                reasons.append(f"нет фрагмента: {token}")
    else:
        if "не найдено подтверждение" not in answer:
            reasons.append("ожидался отказ без подтверждения")

    return not reasons, reasons


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Проверка контрольной выборки вопросов через /api/query.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "reference_questions_ru.json"),
        help="Путь к JSON с контрольными вопросами.",
    )
    parser.add_argument("--base-url", default=settings.api_base_url, help="Базовый URL API.")
    parser.add_argument("--user-id", default="local-evaluator", help="Пользователь для запросов.")
    parser.add_argument("--chat-id", default="local-chat", help="Идентификатор чата.")
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    cases = load_cases(fixture_path)
    passed = 0
    print(f"Контрольных вопросов: {len(cases)}")

    with httpx.Client(timeout=180) as client:
        for index, case in enumerate(cases, start=1):
            response = client.post(
                f"{args.base_url.rstrip('/')}/api/query",
                json={
                    "user_id": args.user_id,
                    "chat_id": args.chat_id,
                    "text": case["question"],
                    "trace_id": f"eval-{index}",
                },
            )
            response.raise_for_status()
            payload = response.json()
            ok, reasons = answer_matches(case, payload)
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {case['id']} :: {case['question']}")
            if reasons:
                print("  Причины: " + "; ".join(reasons))
            if ok:
                passed += 1

    score = round((passed / len(cases)) * 100, 2) if cases else 0.0
    print(f"Итог: {passed}/{len(cases)} ({score}%)")


if __name__ == "__main__":
    main()
