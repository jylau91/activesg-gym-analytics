from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from .config import DB_PATH, LAST_PUBLISH_PATH, PROJECT_ROOT, SGT, check_collection_window, parse_iso_sgt
from .dashboard import export_data
from .scraper import scrape, result_to_json
from .storage import init_db, stats, store_scrape

def _git_has_remote() -> bool:
    return subprocess.run(["git", "remote", "get-url", "origin"], cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def _git_commit_and_push(message: str) -> bool:
    if not (PROJECT_ROOT / ".git").exists() or not _git_has_remote():
        return False
    subprocess.run(["git", "add", "site/data/observations.json", "site/index.html"], cwd=PROJECT_ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROJECT_ROOT)
    if diff.returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], cwd=PROJECT_ROOT, check=True)
    subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True)
    return True

def _publish_due(minutes: int) -> bool:
    now = datetime.now(tz=SGT)
    if not LAST_PUBLISH_PATH.exists():
        return True
    try:
        last = datetime.fromisoformat(LAST_PUBLISH_PATH.read_text().strip()).astimezone(SGT)
    except Exception:
        return True
    return now - last >= timedelta(minutes=minutes)

def collect_once(args: argparse.Namespace) -> int:
    start = parse_iso_sgt(args.start_sgt)
    end = parse_iso_sgt(args.end_sgt)
    if args.respect_window:
        window = check_collection_window(start_sgt=start, end_sgt=end)
        if not window.should_collect:
            if args.verbose:
                print(f"skip: {window.reason}")
            return 0
    result = scrape(timeout=args.timeout)
    snapshot_id = store_scrape(result, db_path=Path(args.db_path))
    export_data(db_path=Path(args.db_path))
    published = False
    if args.publish and _publish_due(args.publish_interval_minutes):
        try:
            published = _git_commit_and_push(f"Update ActiveSG gym data {result.fetched_at_sgt[:16]}")
            LAST_PUBLISH_PATH.write_text(datetime.now(tz=SGT).isoformat())
        except Exception as exc:
            if args.verbose:
                print(f"publish failed: {exc}", file=sys.stderr)
            if args.strict_publish:
                raise
    if args.json:
        print(result_to_json(result))
    elif args.verbose:
        st = stats(Path(args.db_path))
        print(f"stored snapshot_id={snapshot_id} observations={len(result.observations)} total_snapshots={st['snapshot_count']} published={published}")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Collect ActiveSG gym crowd data")
    p.add_argument("--db-path", default=str(DB_PATH))
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--respect-window", action="store_true", help="Only collect during 6am–10pm SGT and optional date range")
    p.add_argument("--start-sgt", default=None)
    p.add_argument("--end-sgt", default=None)
    p.add_argument("--publish", action="store_true", help="Regenerate dashboard and push to GitHub if publish interval elapsed")
    p.add_argument("--publish-interval-minutes", type=int, default=60)
    p.add_argument("--strict-publish", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p

def main(argv: list[str] | None = None) -> int:
    init_db()
    return collect_once(build_parser().parse_args(argv))

if __name__ == "__main__":
    raise SystemExit(main())
