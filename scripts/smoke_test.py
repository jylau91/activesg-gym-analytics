#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activesg_gym_analytics.scraper import scrape
from activesg_gym_analytics.storage import store_scrape, stats
from activesg_gym_analytics.dashboard import export_data
result = scrape()
print(f"parsed {len(result.observations)} gym observations")
for obs in result.observations[:5]:
    print(f"- {obs.gym_name}: {obs.status_text} score={obs.crowd_score}")
snapshot_id = store_scrape(result)
print(f"stored snapshot_id={snapshot_id}")
export_data()
print(stats())
