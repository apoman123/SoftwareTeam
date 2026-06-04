---
name: configure-observability
description: Use when operating a service, to instrument the four golden signals and alert on SLO-threatening symptoms.
tool: write_source_file
---

# Configure observability

Instrument the **four golden signals** — latency, traffic, errors, saturation — with
Prometheus scrape config and Grafana dashboards.

- Define an **SLI** (a measurable reliability indicator), set an **SLO** target on it, and
  derive an **error budget**.
- **Alert on symptoms** that threaten the SLO (high error rate, high p95 latency) and route
  pages to Slack — alert on user-facing impact, not on every blip.
