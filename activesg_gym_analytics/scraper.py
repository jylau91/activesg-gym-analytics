from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from .config import JINA_READER_URL, SOURCE_PAGE_URL, SGT

SKIP_PREFIXES = (
    "title:", "url source:", "markdown content:", "warning:", "image ",
    "book sports", "with balloting", "using our", "selecting gym",
)

@dataclass
class GymObservation:
    gym_name: str
    status_text: str
    is_open: bool | None
    capacity_current: int | None
    capacity_total: int | None
    occupancy_pct: float | None
    crowd_score: float | None
    source_detail: str
    def asdict(self) -> dict:
        return asdict(self)

@dataclass
class ScrapeResult:
    fetched_at_utc: str
    fetched_at_sgt: str
    source_url: str
    reader_url: str
    raw_sha256: str
    raw_text: str
    observations: list[GymObservation]

def _clean_line(line: str) -> str:
    line = re.sub(r"^[-*]\s+", "", line.strip())
    return re.sub(r"\s+", " ", line).strip()

def _looks_like_gym_name(line: str) -> bool:
    low = line.lower()
    if any(low.startswith(p) for p in SKIP_PREFIXES):
        return False
    if "gym" not in low:
        return False
    return "activesg" in low or low.startswith("gym @")

def _parse_capacity(status: str) -> tuple[int | None, int | None, float | None]:
    m = re.search(r"(\d+)\s*/\s*(\d+)", status)
    if not m:
        m = re.search(r"(\d+)\s*(?:of|out of)\s*(\d+)", status, re.I)
    if m:
        cur, total = int(m.group(1)), int(m.group(2))
        return cur, total, round(cur / total * 100, 1) if total else None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", status)
    if m:
        return None, None, float(m.group(1))
    return None, None, None

def _score_status(status: str, occupancy_pct: float | None) -> tuple[bool | None, float | None]:
    low = status.lower()
    if occupancy_pct is not None:
        return (False if "closed" in low else True), occupancy_pct
    if "closed" in low:
        return False, 0.0
    if any(word in low for word in ("full", "very crowded", "packed")):
        return True, 100.0
    if any(word in low for word in ("high", "crowded", "busy", "limited")):
        return True, 75.0
    if any(word in low for word in ("medium", "moderate")):
        return True, 50.0
    if any(word in low for word in ("low", "available", "not crowded", "vacancy", "vacancies")):
        return True, 25.0
    if any(word in low for word in ("open", "operating")):
        return True, None
    return None, None

def parse_markdown(text: str) -> list[GymObservation]:
    lines = [line for line in (_clean_line(x) for x in text.splitlines()) if line]
    observations: list[GymObservation] = []
    current_name: str | None = None
    current_status: list[str] = []
    def flush() -> None:
        nonlocal current_name, current_status
        if not current_name:
            return
        status = " · ".join(current_status).strip() if current_status else "Unknown"
        cur, total, pct = _parse_capacity(status)
        is_open, score = _score_status(status, pct)
        observations.append(GymObservation(current_name, status, is_open, cur, total, pct, score, status))
        current_name = None
        current_status = []
    for line in lines:
        if _looks_like_gym_name(line):
            flush()
            current_name = line
            current_status = []
            continue
        if current_name:
            low = line.lower()
            if any(low.startswith(p) for p in SKIP_PREFIXES):
                continue
            if len(current_status) < 5:
                current_status.append(line)
    flush()
    dedup: dict[str, GymObservation] = {}
    for obs in observations:
        dedup[obs.gym_name] = obs
    return list(dedup.values())

def fetch_markdown(timeout: int = 45) -> str:
    headers = {
        # Jina Reader rejects Python's default urllib UA and can also reject
        # over-specified browser/cache headers. This minimal UA is enough and
        # was verified locally against the ActiveSG reader URL.
        "User-Agent": "Mozilla/5.0",
    }
    reader_url = f"{JINA_READER_URL}?hermes_ts={int(time.time())}"
    req = urllib.request.Request(reader_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {exc.code} fetching reader URL: {detail}") from exc
    if "Performing security verification" in body and "Cloudflare" in body:
        raise RuntimeError("Reader returned Cloudflare challenge instead of crowd data")
    return body

def scrape(timeout: int = 45) -> ScrapeResult:
    fetched_utc = datetime.now(timezone.utc)
    raw = fetch_markdown(timeout=timeout)
    observations = parse_markdown(raw)
    if len(observations) < 10:
        raise RuntimeError(f"Parsed only {len(observations)} gym observations; page format may have changed")
    return ScrapeResult(
        fetched_at_utc=fetched_utc.isoformat(),
        fetched_at_sgt=fetched_utc.astimezone(SGT).isoformat(),
        source_url=SOURCE_PAGE_URL,
        reader_url=JINA_READER_URL,
        raw_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        raw_text=raw,
        observations=observations,
    )

def result_to_json(result: ScrapeResult) -> str:
    return json.dumps({
        "fetched_at_utc": result.fetched_at_utc,
        "fetched_at_sgt": result.fetched_at_sgt,
        "source_url": result.source_url,
        "reader_url": result.reader_url,
        "raw_sha256": result.raw_sha256,
        "observation_count": len(result.observations),
        "observations": [obs.asdict() for obs in result.observations],
    }, ensure_ascii=False, indent=2)
