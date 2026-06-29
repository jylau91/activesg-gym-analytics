#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activesg_gym_analytics.dashboard import export_data
from activesg_gym_analytics.storage import stats
export_data()
print(stats())
