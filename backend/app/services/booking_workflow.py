from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.model.equipment import Equipment
from app.model.laboratory import Laboratory
from app.domain.booking.resolver import resolve_laboratory
from app.services.booking_policy import (
    format_standard_booking_slots,
    is_standard_booking_slot,
)


BOOKING_WORDS = ("\u9884\u7ea6", "\u9884\u8ba2", "\u8ba2\u9605")
BOOKING_VERBS = ("\u5e2e\u6211", "\u6211\u8981", "\u6211\u60f3", "\u8bf7\u5e2e", "\u7533\u8bf7", "\u521b\u5efa")
BOOKING_RESUME_PHRASES = (
    "继续前面的预约",
    "继续刚才的预约",
    "继续之前的预约",
    "继续预约",
    "接着预约",
    "恢复预约",
)
BOOKING_QUERY_PHRASES = (
    "我的预约",
    "预约记录",
    "预约列表",
    "有哪些预约",
    "还有哪些预约",
    "当前预约",
    "查看预约",
    "查询预约",
)
RESOURCE_QUERY_PHRASES = (
    "\u54ea\u4e9b\u5b9e\u9a8c\u5ba4",
    "\u54ea\u4e9b\u8bbe\u5907",
    "\u6709\u54ea\u4e9b\u5b9e\u9a8c\u5ba4",
    "\u6709\u54ea\u4e9b\u8bbe\u5907",
    "\u5b9e\u9a8c\u5ba4\u548c\u8bbe\u5907\u53ef\u4ee5\u9884\u7ea6",
    "\u53ef\u9884\u7ea6\u7684\u5b9e\u9a8c\u5ba4",
    "\u53ef\u9884\u7ea6\u7684\u8bbe\u5907",
    "\u67e5\u8be2\u5b9e\u9a8c\u5ba4\u548c\u8bbe\u5907",
)
DATE_WORDS = {
    "\u4eca\u5929": 0,
    "\u4eca\u65e5": 0,
    "\u660e\u5929": 1,
    "\u540e\u5929": 2,
}
RELATIVE_DAY_PATTERNS = (
    (re.compile(r"(?:一周|一星期|7天)(?:后|以后|之后)"), 7),
    (re.compile(r"(?:两周|两个星期|14天)(?:后|以后|之后)"), 14),
)
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
NORMAL_EQUIPMENT_STATUSES = {"正常", "Normal", "姝ｅ父"}


def is_resource_query_intent(text: str) -> bool:
    normalized = (text or "").strip()
    if not any(phrase in normalized for phrase in RESOURCE_QUERY_PHRASES):
        return False
    explicit_create = (
        "\u5e2e\u6211\u9884\u7ea6",
        "\u6211\u8981\u9884\u7ea6",
        "\u6211\u60f3\u9884\u7ea6",
        "\u8bf7\u5e2e\u6211\u9884\u7ea6",
        "\u7533\u8bf7\u9884\u7ea6",
        "\u521b\u5efa\u9884\u7ea6",
    )
    if any(phrase in normalized for phrase in explicit_create):
        return False
    return not any(word in normalized for word in DATE_WORDS) and not re.search(
        r"\d{1,2}(?:\u70b9|:\d{2})",
        normalized,
    )


def is_create_booking_intent(text: str) -> bool:
    normalized = (text or "").strip()
    if is_resource_query_intent(normalized):
        return False
    if is_booking_query_intent(normalized):
        return False
    if not any(word in normalized for word in BOOKING_WORDS):
        return False
    return normalized.startswith(BOOKING_WORDS) or any(
        verb in normalized for verb in BOOKING_VERBS
    )


def is_booking_query_intent(text: str) -> bool:
    normalized = (text or "").strip()
    if any(phrase in normalized for phrase in ("取消预约", "取消我的预约", "撤销预约", "取消预订")):
        return False
    return any(phrase in normalized for phrase in BOOKING_QUERY_PHRASES)


def is_booking_resume_intent(text: str) -> bool:
    normalized = (text or "").strip().casefold()
    return normalized in BOOKING_RESUME_PHRASES or normalized == "继续"


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

    for pattern, offset in RELATIVE_DAY_PATTERNS:
        if pattern.search(text):
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
    result = resolve_laboratory(db, text)
    return result.laboratory, result.ambiguous, list(result.candidates)


def _equipment_stem(value: str) -> str:
    normalized = _normalize_phrase(value)
    for suffix in ("设备", "仪器"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _equipment_query_score(text: str, equipment: Equipment) -> int:
    query = _normalize_phrase(text)
    name = _normalize_phrase(equipment.name or "")
    equipment_type = _normalize_phrase(equipment.equipment_type or "")
    model = _normalize_phrase(equipment.model or "")
    name_stem = _equipment_stem(name)
    if not name:
        return 0
    if name in query:
        return 100
    if name_stem and len(name_stem) >= 2 and name_stem in query:
        return 95
    if equipment_type and len(equipment_type) >= 2 and equipment_type in query:
        return 90
    if model and len(model) >= 2 and model in query:
        return 85
    similarity = SequenceMatcher(None, name, query).ratio()
    if similarity >= 0.72:
        return int(similarity * 70)
    return 0


def _resolve_equipment(
    db: Session,
    text: str,
    laboratory_id: int,
) -> tuple[Equipment | None, bool, list[str]]:
    equipment_rows = (
        db.query(Equipment)
        .filter(
            Equipment.laboratory_id == laboratory_id,
            Equipment.status == 1,
            Equipment.maintenance_status.in_(NORMAL_EQUIPMENT_STATUSES),
        )
        .order_by(Equipment.id)
        .all()
    )
    scored = [
        (item, _equipment_query_score(text, item))
        for item in equipment_rows
    ]
    scored = [(item, score) for item, score in scored if score > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    if not scored:
        return None, False, []
    best_item, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0
    if len(scored) > 1 and second_score >= best_score - 8:
        return None, True, [item.name for item, _ in scored[:5]]
    if best_score >= 75:
        return best_item, False, []
    return None, False, []


def resolve_booking_request(
    db: Session,
    text: str,
    now: datetime | None = None,
    existing_draft: dict[str, Any] | None = None,
    workflow_active: bool = False,
    resume_requested: bool = False,
) -> dict[str, Any]:
    existing_draft = existing_draft or {}
    current_time = now or datetime.now(LOCAL_TZ)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(LOCAL_TZ).replace(tzinfo=None)

    laboratory, ambiguous, candidates = _resolve_laboratory(db, text)
    current_date = _parse_date(text, current_time)
    current_time_range = _parse_time_range(text)
    has_slot_signal = bool(
        laboratory
        or ambiguous
        or current_date
        or current_time_range
        or any(word in text for word in ("预约", "预订", "改成", "换成"))
    )
    if not is_create_booking_intent(text) and not (
        workflow_active and (has_slot_signal or resume_requested)
    ):
        return {"handled": False}

    draft: dict[str, Any] = dict(existing_draft)
    if laboratory is not None:
        draft.update(
            {
                "laboratory_id": laboratory.id,
                "laboratory_name": laboratory.name,
            }
        )
    if ambiguous:
        candidate_text = "、".join(candidates[:5])
        return {
            "handled": True,
            "ready": False,
            "message": f"请明确要预约哪一间实验室，可选：{candidate_text}。",
            "reason": "ambiguous_laboratory",
            "missing_fields": ["laboratory"],
            "draft": draft,
        }

    if draft.get("laboratory_id") is None:
        return {
            "handled": True,
            "ready": False,
            "message": "没有识别到对应的开放实验室，请提供实验室名称或所在位置。",
            "reason": "missing_laboratory",
            "missing_fields": ["laboratory"],
            "draft": draft,
        }

    equipment, equipment_ambiguous, equipment_candidates = _resolve_equipment(
        db,
        text,
        draft["laboratory_id"],
    )
    if equipment_ambiguous:
        candidate_text = "、".join(equipment_candidates[:5])
        return {
            "handled": True,
            "ready": False,
            "message": f"请明确要预约哪一件设备，可选：{candidate_text}。",
            "reason": "ambiguous_equipment",
            "missing_fields": ["equipment"],
            "draft": draft,
        }
    if equipment is not None:
        draft.update(
            {
                "equipment_ids": [equipment.id],
                "equipment": [{"id": equipment.id, "name": equipment.name}],
            }
        )
    elif not draft.get("equipment_ids") and any(
        word in text for word in ("设备", "仪器", "显微镜")
    ):
        return {
            "handled": True,
            "ready": False,
            "message": "没有找到该实验室下可预约的对应设备，请提供设备名称。",
            "reason": "equipment_not_found",
            "missing_fields": ["equipment"],
            "draft": draft,
        }

    booking_date = current_date
    time_range = current_time_range
    if booking_date is None and draft.get("start_time"):
        try:
            booking_date = datetime.strptime(draft["start_time"], "%Y-%m-%d %H:%M").date()
        except (TypeError, ValueError):
            booking_date = None
    if time_range is None and draft.get("start_time") and draft.get("end_time"):
        try:
            draft_start = datetime.strptime(draft["start_time"], "%Y-%m-%d %H:%M")
            draft_end = datetime.strptime(draft["end_time"], "%Y-%m-%d %H:%M")
            time_range = (draft_start.hour, draft_start.minute, draft_end.hour, draft_end.minute)
        except (TypeError, ValueError):
            time_range = None

    if booking_date is None and time_range is None:
        return {
            "handled": True,
            "ready": False,
            "message": "请补充预约日期和时间段，例如“明天 14:00–16:00”。",
            "reason": "missing_date_and_time",
            "missing_fields": ["date", "time"],
            "draft": draft,
        }
    if booking_date is None:
        return {
            "handled": True,
            "ready": False,
            "message": f"时间段已识别为 {time_range[0]:02d}:{time_range[1]:02d}–{time_range[2]:02d}:{time_range[3]:02d}，请补充预约日期。",
            "reason": "missing_date",
            "missing_fields": ["date"],
            "draft": draft,
        }
    if time_range is None:
        return {
            "handled": True,
            "ready": False,
            "message": f"预约日期已识别为 {booking_date.strftime('%Y-%m-%d')}，请补充预约时间段。",
            "reason": "missing_time",
            "missing_fields": ["time"],
            "draft": draft,
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
            "draft": draft,
        }
    if start >= end:
        return {
            "handled": True,
            "ready": False,
            "message": "结束时间必须晚于开始时间，请重新提供时间段。",
            "reason": "invalid_time_range",
            "draft": draft,
        }
    if not is_standard_booking_slot(time_range):
        return {
            "handled": True,
            "ready": False,
            "message": (
                f"已识别预约日期为 {booking_date.strftime('%Y-%m-%d')}，"
                f"但 {start.strftime('%H:%M')}–{end.strftime('%H:%M')} 不属于可预约时段。"
                f"请选择：{format_standard_booking_slots()}。"
            ),
            "reason": "invalid_standard_slot",
            "draft": draft,
        }
    if start < current_time.replace(second=0, microsecond=0):
        return {
            "handled": True,
            "ready": False,
            "message": "预约时间不能早于当前时间，请重新提供预约日期和时间段。",
            "reason": "time_in_past",
            "draft": draft,
        }

    return {
        "handled": True,
        "ready": True,
        "laboratory_id": draft["laboratory_id"],
        "laboratory_name": draft.get("laboratory_name"),
        "start_time": start.strftime("%Y-%m-%d %H:%M"),
        "end_time": end.strftime("%Y-%m-%d %H:%M"),
        "purpose": "实验室/设备预约",
        "student_count": 1,
        "equipment_ids": draft.get("equipment_ids", []),
        "draft": {
            **draft,
            "laboratory_id": draft.get("laboratory_id"),
            "laboratory_name": draft.get("laboratory_name"),
            "start_time": start.strftime("%Y-%m-%d %H:%M"),
            "end_time": end.strftime("%Y-%m-%d %H:%M"),
        },
    }
