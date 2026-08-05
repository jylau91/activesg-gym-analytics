import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CronScriptTests(unittest.TestCase):
    def test_collector_has_no_fixed_date_range(self):
        script = (PROJECT_ROOT / "scripts" / "cron_collect.sh").read_text(encoding="utf-8")
        self.assertNotIn("START_SGT=", script)
        self.assertNotIn("END_SGT=", script)
        self.assertNotIn("--start-sgt", script)
        self.assertNotIn("--end-sgt", script)
        self.assertIn("--respect-window", script)


if __name__ == "__main__":
    unittest.main()
