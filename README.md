# ActiveSG Gym Crowd Analytics

Silent local logger + static analytics dashboard for the public ActiveSG gym crowd page.

Live dashboard: https://jylau91.github.io/activesg-gym-analytics/

Repository: https://github.com/jylau91/activesg-gym-analytics

## What it does

- Scrapes `https://activesg.gov.sg/gym-pool-crowd` via a text reader snapshot.
- Tracks all parsed ActiveSG gyms in SQLite.
- Runs only during ActiveSG opening hours: **6am–10pm Singapore time**.
- Generates a browser dashboard in `site/index.html` with Plotly charts.
- Can publish the static dashboard to GitHub Pages.

No personal data is collected; only public gym status/crowd labels from ActiveSG are stored.

## Local commands

```bash
cd ~/Projects/activesg-gym-analytics
python3 -m activesg_gym_analytics.collector --verbose
python3 scripts/export_dashboard.py
open site/index.html
```

## Scheduled collection

Hermes cron runs `activesg_gym_collect.sh` from `~/.hermes/scripts/` every 15 minutes while the Mac mini is awake. The script points back to this project and is also versioned at `scripts/cron_collect.sh`.

- Cron job ID: `a0c901f80b0b`
- Schedule: `*/15 6-22 * * *`
- Repeat: `2108` ticks, covering the Jun 30–Jul 30 2026 collection window
- True collection window enforced by script: **2026-06-30 06:00 SGT → 2026-07-30 22:00 SGT**
- Success behavior: silent; no Telegram messages
- Logs: `logs/collector.log`

The collector stores data locally on the Mac mini and publishes the GitHub Pages dashboard at most hourly after new samples are collected.

Management:

```bash
hermes cron list
hermes cron pause a0c901f80b0b
hermes cron resume a0c901f80b0b
hermes cron remove a0c901f80b0b
```

## Data

- SQLite database: `data/activesg_gym.sqlite`
- Dashboard data JSON: `site/data/observations.json`

## Caveats

- The official page is protected by Cloudflare for direct browser/curl traffic, so the logger uses Jina Reader as a markdown snapshot source.
- The parser stores raw status text and best-effort numeric fields. If ActiveSG changes the page shape, the logger will error rather than silently record bad data.
- The dashboard is most useful after several days of samples.
