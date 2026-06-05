---
name: containerize-service
description: Writes a small, reproducible, 12-factor Dockerfile. Use when packaging a service for deployment.
tool: write_source_file
---

# Containerise the service

Write a Dockerfile that builds a small, reproducible image:

- A **slim base**; install dependencies in a cached layer **before** copying app code.
- **No secrets baked in**; an explicit `CMD`.
- Treat config as **environment variables** (12-factor) so the same image runs in every environment.
