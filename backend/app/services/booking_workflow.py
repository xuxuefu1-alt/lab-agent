from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.model.laboratory import Laboratory


BOOKING_WORDS = ("\u9884\u7ea6", "\u9884\u8ba2", "\u8ba2\u9605")
BOOKING_VERBS = ("\u5e2e\u6211", "\u6211\u8981", "\u6211\u60f3", "\u8bf7\u5e2e", "\u7533\u8bf7", "\u521b\u5efa")
DATE_WORDS = {
    "\u4eca\u5929": 0,
    "\u4eca\u65e5": 0,
    "\u660e\u5929": 1,
    "\u540e\u5929": 2,
}
AM_WORDS = {"\u4e0a\u5348", "\u51cc\u6668"}
PM_WORDS = {"\u4e0b\u5348", "\u665a\u4e0a"}
WEEKDAY_WORDS = {
    "\u4e00": 0,
    "\u4e8c": 1,
    "\u4e09": 2,
    "\u56db": 3,
    "\u4e94": 4,
    "\u516d": 5,
    "\u65e5": 6,
    "\u5929": 6,
}
LOCAL_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def is_create_booking_intent(text: str) -> bool:
    normalized = (text or "").strip()
    if not any(word in normalized for word in BOOKING_WORDS):
        return False
    return normalized.startswith(BOOKING_WORDS) or any(
        verb in normalized for verb in BOOKING_VERBS
    )


def _parse_date(text: str, now: datetime) -> datetime.date | None:
    explicit = re.search(
        r"(20\d{2})[-/\u5e74](\d{1,2})[-/\u6708](\d{1,2})\u65e5?",
        text,
    )
    if explicit:
        try:
            return datetime(
                int(explicit.group(1)),
                int(explicit.group(2)),
                int(explicit.group(3)),
            ).date()
        except ValueError:
            return None

    month_day = re.search(r"(?:(20\d{2})\u5e74)?(\d{1,2})\u6708(\d{1,2})\u65e5?", text)
    if month_day:
        year = int(month_day.group(1) or now.year)
        try:
            candidate = datetime(
                year,
                int(month_day.group(2)),
                int(month_day.group(3)),
            ).date()
        except ValueError:
            return None
        if month_day.group(1) is None and candidate < now.date():
            candidate = candidate.replace(year=year + 1)
        return candidate

    numeric_month_day = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text)
    if numeric_month_day:
        try:
            candidate = datetime(
                now.year,
                int(numeric_month_day.group(1)),
                int(numeric_month_day.group(2)),
            ).date()
        except ValueError:
            return None
        if candidate < now.date():
            candidate = candidate.replace(year=now.year + 1)
        return candidate

    for word, offset in DATE_WORDS.items():
        if word in text:
            return (now + timedelta(days=offset)).date()

    weekday = re.search(r"(?:(\u672c\u5468|\u8fd9\u5468|\u4e0b\u5468))?[\u5468\u661f](\u4e00|\u4e8c|\u4e09|\u56db|\u4e94|\u516d|\u65e5|\u5929)", text)
    if weekday:
        prefix, weekday_word = weekday.groups()
        target = WEEKDAY_WORDS[weekday_word]
        monday = now.date() - timedelta(days=now.weekday())
        if prefix == "\u4e0b\u5468":
            return monday + timedelta(days=7 + target)
        candidate = monday + timedelta(days=target)
        if prefix in {"\u672c\u5468", "\u8fd9\u5468"}:
            return candidate
        if candidate <= now.date():
            candidate += timedelta(days=7)
        return candidate
    return None


def _to_24_hour(hour: int, meridiem: str | None) -> int:
    if meridiem in PM_WORDS and hour < 12:
        return hour + 12
    if meridiem in AM_WORDS and hour == 12:
        return 0
    return hour


def _parse_time_range(text: str) -> tuple[int, int, int, int] | None:
    chinese = re.search(
        r"(?:(上午|中午|下午|晚上|凌晨)\s*)?(\d{1,2})(?:点|时)(?:(\d{1,2})\s*分?)?\s*"
        r"(?:到|至|[-~])\s*(?:(上午|中午|下午|晚上|凌晨)\s*)?(\d{1,2})"
        r"(?:点|时)(?:(\d{1,2})\s*分?)?",
        text,
    )
    if chinese:
        start_ampm, start_hour, start_minute, end_ampm, end_hour, end_minute = chinese.groups()
        end_ampm = end_ampm or start_ampm
        return (
            _to_24_hour(int(start_hour), start_ampm),
            int(start_minute or 0),
            _to_24_hour(int(end_hour), end_ampm),
            int(end_minute or 0),
        )

    numeric = re.search(
        r"(\d{1,2}):(\d{2})\s*(?:到|至|[-~])\s*(\d{1,2}):(\d{2})",
        text,
    )
    if numeric:
        return tuple(int(value) for value in numeric.groups())  # type: ignore[return-value]
    return None


def _normalize_phrase(value: str) -> str:
    return re.sub(r"[\s,，。.!！？?：:、]", "", value).casefold()


LABORATORY_GENERIC_WORDS = ("实验室", "实验", "实验室的")


def _laboratory_stem(value: str) -> str:
    normalized = _normalize_phrase(value)
    for suffix in LABORATORY_GENERIC_WORDS:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _laboratory_query_score(text: str, laboratory: Laboratory) -> int:
    query = _normalize_phrase(text)
    name = _normalize_phrase(laboratory.name or "")
    stem = _laboratory_stem(name)
    location = _normalize_phrase(laboratory.location or "")

    if not name:
        return 0
    if name in query:
        return 100
    if stem and len(stem) >= 2 and stem in query:
        return 95

    # A location plus a generic laboratory reference is a valid shorthand
    # only when the location resolves to one active laboratory.
    if location and location in query and any(word in query for word in ("实验室", "实验")):
        return 80

    # Keep fuzzy matching conservative and only use it when the query has
    # meaningful overlap with the laboratory name.
    similarity = SequenceMatcher(None, name, query).ratio()
    if similarity >= 0.72:
        return int(similarity * 70)
    return 0


def _resolve_laboratory(
    db: Session,
    text: str,
) -> tuple[Laboratory | None, bool, list[str]]:
    laboratories = (
        db.query(Laboratory)
        .filter(Laboratory.status == 1)
        .order_by(Laboratory.id)
        .all()
    )
    scored = [
        (item, _laboratory_query_score(text, item))
        for item in laboratories
    ]
    scored = [(item, score) for item, score in scored if score > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    if not scored:
        return None, False, []

    best_item, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0
    # A close second candidate means the shorthand is ambiguous. Never guess.
    if len(scored) > 1 and second_score >= best_score - 8:
        return None, True, [item.name for item, _ in scored[:5]]
    if best_score >= 75:
        return best_item, False, []
    return None, False, []


def resolve_booking_request(
    db: Session,
    text: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not is_create_booking_intent(text):
        return {"handled": False}

    current_time = now or datetime.now(LOCAL_TZ)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(LOCAL_TZ).replace(tzinfo=None)
    laboratory, ambiguous, candidates = _resolve_laboratory(db, text)
    if ambiguous:
        candidate_text = "、".join(candidates[:5])
        return {
            "handled": True,
            "ready": False,
            "message": f"请明确要预约哪一间实验室，可选：{candidate_text}。",
            "reason": "ambiguous_laboratory",
        }
    if laboratory is None:
        return {
            "handled": True,
            "ready": False,
            "message": "没有识别到对应的开放实验室，请提供实验室名称或所在位置。",
            "reason": "missing_laboratory",
        }

    booking_date = _parse_date(text, current_time)
    time_range = _parse_time_range(text)
    if booking_date is None or time_range is None:
        return {
            "handled": True,
            "ready": False,
            "message": "请补充预约日期与时间段，我再确认预约信息。",
            "reason": "missing_date_or_time",
        }

    start_hour, start_minute, end_hour, end_minute = time_range
    try:
        start = datetime.combine(
            booking_date,
            datetime.min.time().replace(hour=start_hour, minute=start_minute),
        )
        end = datetime.combine(
            booking_date,
            datetime.min.time().replace(hour=end_hour, minute=end_minute),
        )
    except ValueError:
        return {
            "handled": True,
            "ready": False,
            "message": "预约时间格式不正确，请重新提供开始和结束时间。",
            "reason": "invalid_time",
        }
    if start >= end:
        return {
            "handled": True,
            "ready": False,
            "message": "结束时间必须晚于开始时间，请重新提供时间段。",
            "reason": "invalid_time_range",
        }
    if start < current_time.replace(second=0, microsecond=0):
        return {
            "handled": True,
            "ready": False,
            "message": "预约时间不能早于当前时间，请重新提供预约日期和时间段。",
            "reason": "time_in_past",
        }

    return {
        "handled": True,
        "ready": True,
        "laboratory_id": laboratory.id,
        "laboratory_name": laboratory.name,
        "start_time": start.strftime("%Y-%m-%d %H:%M"),
        "end_time": end.strftime("%Y-%m-%d %H:%M"),
        "purpose": "实验室/设备预约",
        "student_count": 1,
        "equipment_ids": [],
    }
