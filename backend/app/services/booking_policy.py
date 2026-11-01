from __future__ import annotations

from datetime import datetime


# The booking policy is shared by the AI workflow and direct booking APIs.
STANDARD_BOOKING_SLOTS: tuple[tuple[int, int, int, int], ...] = (
    (8, 0, 10, 0),
    (10, 0, 12, 0),
    (14, 0, 16, 0),
    (16, 0, 18, 0),
    (19, 0, 21, 0),
)


# 判断standard booking slot相关数据或业务逻辑。
def is_standard_booking_slot(time_range: tuple[int, int, int, int]) -> bool:
    return time_range in STANDARD_BOOKING_SLOTS


# 负责 format standard booking slots 相关逻辑，并返回处理结果。
def format_standard_booking_slots() -> str:
    return "、".join(
        f"{start_hour:02d}:{start_minute:02d}–{end_hour:02d}:{end_minute:02d}"
        for start_hour, start_minute, end_hour, end_minute in STANDARD_BOOKING_SLOTS
    )


# 负责 time range from datetimes 相关逻辑，并返回处理结果。
def time_range_from_datetimes(start: datetime, end: datetime) -> tuple[int, int, int, int]:
    return start.hour, start.minute, end.hour, end.minute

