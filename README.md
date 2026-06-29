# ActiveSG Gym Crowd Analytics

Silent local logger + static analytics dashboard for the public ActiveSG gym crowd page.

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

Hermes cron runs `scripts/collect_once.py` every 15 minutes during the 6am–10pm window. The script is silent on success. It stores data locally on the Mac mini and publishes the dashboard at most hourly if GitHub Pages is configured.

## Data

- SQLite database: `data/activesg_gym.sqlite`
- Dashboard data JSON: `site/data/observations.json`

## Caveats

- The official page is protected by Cloudflare for direct browser/curl traffic, so the logger uses Jina Reader as a markdown snapshot source.
- The parser stores raw status text and best-effort numeric fields. If ActiveSG changes the page shape, the logger will error rather than silently record bad data.
- The dashboard is most useful after several days of samples.
