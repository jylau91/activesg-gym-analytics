from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
SITE_DIR = PROJECT_ROOT / "site"
DB_PATH = DATA_DIR / "activesg_gym.sqlite"
LAST_PUBLISH_PATH = DATA_DIR / ".last_publish_sgt"
SOURCE_PAGE_URL = "https://activesg.gov.sg/gym-pool-crowd"
JINA_READER_URL = "https://r.jina.ai/http://https://activesg.gov.sg/gym-pool-crowd"
OPEN_TIME = time(6, 0)
CLOSE_TIME = time(22, 0)
DEFAULT_SAMPLE_MINUTES = 15
DEFAULT_PUBLISH_MINUTES = 60
DEFAULT_COLLECTION_DAYS = 31

@dataclass(frozen=True)
class WindowCheck:
    now_sgt: datetime
    start_sgt: datetime
    end_sgt: datetime
    within_daily_hours: bool
    within_date_range: bool
    should_collect: bool
    reason: str

def now_sgt() -> datetime:
    return datetime.now(tz=SGT)

def default_end_sgt(start: datetime | None = None) -> datetime:
    start = start or now_sgt()
    return start + timedelta(days=DEFAULT_COLLECTION_DAYS)

def parse_iso_sgt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SGT)
    return dt.astimezone(SGT)

def check_collection_window(start_sgt: datetime | None = None, end_sgt: datetime | None = None, now: datetime | None = None) -> WindowCheck:
    now = (now or now_sgt()).astimezone(SGT)
    start_sgt = (start_sgt or now.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(SGT)
    end_sgt = (end_sgt or default_end_sgt(start_sgt)).astimezone(SGT)
    current_time = now.time().replace(second=0, microsecond=0)
    within_daily = OPEN_TIME <= current_time <= CLOSE_TIME
    within_range = start_sgt <= now <= end_sgt
    if not within_range:
        reason = f"outside collection date range ({start_sgt.isoformat()} to {end_sgt.isoformat()})"
    elif not within_daily:
        reason = f"outside daily opening hours ({OPEN_TIME.strftime('%H:%M')}–{CLOSE_TIME.strftime('%H:%M')} SGT)"
    else:
        reason = "within collection window"
    return WindowCheck(now, start_sgt, end_sgt, within_daily, within_range, within_daily and within_range, reason)
