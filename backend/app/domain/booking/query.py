from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


LOCAL_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


@dataclass(frozen=True)
class PendingBookingQuery:
    status: str = "待审核"
    time_from: str | None = None
    time_to: str | None = None
    time_label: str = "全部时间"

    def as_tool_params(self) -> dict[str, str]:
        params: dict[str, str] = {"status": self.status}
        if self.time_from:
            params["time_from"] = self.time_from
        if self.time_to:
            params["time_to"] = self.time_to
        return params


def _day_bounds(day: date) -> tuple[str, str]:
    next_day = day + timedelta(days=1)
    return (
        f"{day.isoformat()} 00:00",
        f"{next_day.isoformat()} 00:00",
    )


def _month_bounds(day: date) -> tuple[str, str]:
    start = day.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return (
        f"{start.isoformat()} 00:00",
        f"{end.isoformat()} 00:00",
    )


def _parse_explicit_date(text: str, now: date) -> date | None:
    match = re.search(r"(?<!\d)(20\d{2})[-/]?(\d{1,2})[-/]?(\d{1,2})(?!\d)", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    match = re.search(r"(\d{1,2})月(\d{1,2})日?", text)
    if match:
        try:
            candidate = date(now.year, int(match.group(1)), int(match.group(2)))
        except ValueError:
            return None
        if candidate < now:
            candidate = candidate.replace(year=now.year + 1)
        return candidate

    if "今天" in text or "今日" in text:
        return now
    if "明天" in text:
        return now + timedelta(days=1)
    if "后天" in text:
        return now + timedelta(days=2)
    return None


def resolve_pending_booking_query(text: str, now: datetime | None = None) -> PendingBookingQuery:
    current = now or datetime.now(LOCAL_TZ)
    if current.tzinfo is not None:
        current = current.astimezone(LOCAL_TZ)
    today = current.date()
    normalized = re.sub(r"\s+", "", text or "")

    if "最近一个月" in normalized or "近一个月" in normalized or "过去一个月" in normalized:
        start = today - timedelta(days=30)
        _, today_end = _day_bounds(today)
        return PendingBookingQuery(
            time_from=f"{start.isoformat()} 00:00",
            time_to=today_end,
            time_label="最近一个月",
        )

    if "本月" in normalized or "这个月" in normalized or "当前月" in normalized:
        start, end = _month_bounds(today)
        return PendingBookingQuery(time_from=start, time_to=end, time_label="本月")

    if "本周" in normalized or "这周" in normalized:
        start_day = today - timedelta(days=today.weekday())
        start, _ = _day_bounds(start_day)
        end_day = start_day + timedelta(days=7)
        _, end = _day_bounds(end_day - timedelta(days=1))
        return PendingBookingQuery(time_from=start, time_to=end, time_label="本周")

    explicit = _parse_explicit_date(normalized, today)
    if explicit is not None:
        start, end = _day_bounds(explicit)
        label = "今天" if explicit == today else explicit.isoformat()
        return PendingBookingQuery(time_from=start, time_to=end, time_label=label)

    return PendingBookingQuery()
