"""Canned, deterministic artifacts for `--dry-run` mode.

These let the whole graph + file generation be verified with no Ollama server. The
software-engineer output is a real, runnable FastAPI "Task API" whose pure-logic unit
tests pass with only pytest installed (the FastAPI E2E tests `importorskip` if FastAPI
isn't present). Live mode replaces all of this with actual model generations.
"""

from __future__ import annotations

from .skills.common.authoring import file_blocks

# --------------------------------------------------------------------------- #
# Generated application source (Task API)
# --------------------------------------------------------------------------- #

_SERVICE_PY = '''\
"""In-memory Task service: pure business logic, no web framework required."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count


class TaskError(Exception):
    """Invalid task operation (e.g. bad input)."""


class TaskNotFound(TaskError):
    """Requested task does not exist."""


@dataclass
class Task:
    id: int
    title: str
    done: bool = False


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._ids = count(1)

    def create(self, title: str) -> Task:
        title = (title or "").strip()
        if not title:
            raise TaskError("title must not be empty")
        task = Task(id=next(self._ids), title=title)
        self._tasks[task.id] = task
        return task

    def list(self) -> list[Task]:
        return list(self._tasks.values())

    def get(self, task_id: int) -> Task:
        if task_id not in self._tasks:
            raise TaskNotFound(f"task {task_id} not found")
        return self._tasks[task_id]

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.done = True
        return task

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        del self._tasks[task_id]
'''

_MAIN_PY = '''\
"""FastAPI wiring over the pure TaskService."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .service import TaskError, TaskNotFound, TaskService

app = FastAPI(title="Task API", version="1.0.0")
service = TaskService()


class TaskIn(BaseModel):
    title: str


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskIn) -> TaskOut:
    try:
        task = service.create(payload.title)
    except TaskError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TaskOut(**task.__dict__)


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks() -> list[TaskOut]:
    return [TaskOut(**t.__dict__) for t in service.list()]


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int) -> TaskOut:
    try:
        task = service.get(task_id)
    except TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return TaskOut(**task.__dict__)


@app.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int) -> TaskOut:
    try:
        task = service.complete(task_id)
    except TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return TaskOut(**task.__dict__)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    try:
        service.delete(task_id)
    except TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
'''

_UNIT_TESTS = '''\
"""Unit tests for the pure TaskService (no web framework needed)."""
import pytest

from app.service import TaskError, TaskNotFound, TaskService


def test_create_and_get():
    svc = TaskService()
    task = svc.create("write tests")
    assert task.id == 1
    assert svc.get(1).title == "write tests"


def test_create_empty_title_rejected():
    svc = TaskService()
    with pytest.raises(TaskError):
        svc.create("   ")


def test_complete_marks_done():
    svc = TaskService()
    task = svc.create("ship it")
    assert svc.complete(task.id).done is True


def test_get_missing_raises():
    svc = TaskService()
    with pytest.raises(TaskNotFound):
        svc.get(999)


def test_delete_removes_task():
    svc = TaskService()
    task = svc.create("temp")
    svc.delete(task.id)
    with pytest.raises(TaskNotFound):
        svc.get(task.id)
'''

_REQUIREMENTS = """\
fastapi>=0.110
uvicorn>=0.29
pydantic>=2.7
httpx>=0.27
pytest>=8.0
"""

SWE_FILES = {
    "app/__init__.py": '"""Task API application package."""\n',
    "app/service.py": _SERVICE_PY,
    "app/main.py": _MAIN_PY,
    "tests/__init__.py": "",
    "tests/test_service.py": _UNIT_TESTS,
    "requirements.txt": _REQUIREMENTS,
}

# --------------------------------------------------------------------------- #
# QA end-to-end tests
# --------------------------------------------------------------------------- #

_E2E_TESTS = '''\
"""End-to-end API tests via FastAPI TestClient (skipped if FastAPI is absent)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_task_crud_flow():
    created = client.post("/tasks", json={"title": "buy milk"})
    assert created.status_code == 201
    task_id = created.json()["id"]

    assert client.get(f"/tasks/{task_id}").json()["title"] == "buy milk"
    assert client.post(f"/tasks/{task_id}/complete").json()["done"] is True
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_empty_title_rejected():
    resp = client.post("/tasks", json={"title": "   "})
    assert resp.status_code == 400
'''

QA_FILES = {"tests/test_e2e.py": _E2E_TESTS}

# --------------------------------------------------------------------------- #
# DevOps / SRE artifacts
# --------------------------------------------------------------------------- #

CI_FILES = {
    "Dockerfile": """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    ".github/workflows/ci.yml": """\
name: CI
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: ruff check . || true
      - run: pytest -q
""",
}

CD_FILES = {
    ".github/workflows/cd.yml": """\
name: CD
on:
  push:
    branches: [main]
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t task-api:${{ github.sha }} .
      - name: Deploy (canary -> full)
        run: echo "kubectl set image deploy/task-api task-api=task-api:${{ github.sha }}"
""",
    "terraform/main.tf": """\
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

variable "image_tag" {
  type    = string
  default = "latest"
}

resource "kubernetes_namespace" "app" {
  metadata {
    name = "task-api"
  }
}
""",
    "k8s/deployment.yaml": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-api
  namespace: task-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: task-api
  template:
    metadata:
      labels:
        app: task-api
    spec:
      containers:
        - name: task-api
          image: task-api:latest
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 10
""",
    "k8s/service.yaml": """\
apiVersion: v1
kind: Service
metadata:
  name: task-api
  namespace: task-api
spec:
  selector:
    app: task-api
  ports:
    - port: 80
      targetPort: 8000
""",
}

# --------------------------------------------------------------------------- #
# Operate / Monitor artifacts
# --------------------------------------------------------------------------- #

OPERATE_FILES = {
    "monitoring/prometheus.yml": """\
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: task-api
    metrics_path: /metrics
    static_configs:
      - targets: ["task-api.task-api.svc:80"]
""",
    "monitoring/alerts.yml": """\
groups:
  - name: task-api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "Task API 5xx error rate above 5%"
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warn
        annotations:
          summary: "Task API p95 latency above 500ms"
""",
    "docs/runbook.md": """\
# Task API On-Call Runbook

## Service overview
FastAPI service exposing CRUD over tasks. Stateless; scale horizontally.

## Alerts
- **HighErrorRate** — check recent deploy, `kubectl logs deploy/task-api`, roll back if needed.
- **HighLatency** — inspect upstream/datastore, check pod CPU/memory.

## Common operations
- Logs: `kubectl logs -f deploy/task-api -n task-api`
- Roll back: `kubectl rollout undo deploy/task-api -n task-api`
- Scale: `kubectl scale deploy/task-api --replicas=4 -n task-api`

## Disaster recovery
- Nightly DB snapshots (when persistence is added); restore from latest snapshot.
- Re-apply IaC: `terraform apply` then `kubectl apply -f k8s/`.
""",
}

# --------------------------------------------------------------------------- #
# Narrative documents
# --------------------------------------------------------------------------- #

_PM_DOC = """\
# Product Backlog — Task API

## Goal
Let users track simple tasks via an HTTP API (create, list, complete, delete).

## User Stories
- **US-1**: As a user, I want to create a task with a title so that I can remember work to do.
- **US-2**: As a user, I want to list my tasks so that I can see everything outstanding.
- **US-3**: As a user, I want to mark a task complete so that I can track progress.
- **US-4**: As a user, I want to delete a task so that I can remove mistakes.

## Acceptance Criteria (Gherkin)
```gherkin
Scenario: Create a task
  Given the API is running
  When I POST /tasks with title "buy milk"
  Then I receive 201 and a task with that title and done=false

Scenario: Reject empty title
  When I POST /tasks with an empty title
  Then I receive 400

Scenario: Complete a task
  Given a task exists
  When I POST /tasks/{id}/complete
  Then the task's done flag is true
```

## Prioritised Backlog (MoSCoW)
- **Must**: US-1, US-2, US-3
- **Should**: US-4
- **Could**: due dates, tags
- **Won't (now)**: multi-user auth, persistence
"""

_UX_DOC = """\
# UX — Task API (API-first, minimal console client)

## User Flow
1. User lists tasks -> sees outstanding items.
2. User adds a task -> item appears with done=false.
3. User completes a task -> item shows done=true.
4. User deletes a task -> item disappears.

## Wireframe (reference console client)
```
+--------------------------------------------------+
|  TASKS                                           |
+--------------------------------------------------+
|  [ ] (1) buy milk                  [done][del]   |
|  [x] (2) write report              [done][del]   |
+--------------------------------------------------+
|  New task: [__________________________] [ Add ]  |
+--------------------------------------------------+
```

## Component / State Notes
- Empty state: "No tasks yet — add your first one."
- Error toast on 400 (empty title) and 404 (missing task).
"""

_TL_DOC = """\
# Architecture & Technical Design — Task API

## Tech Stack
- Language: Python 3.12
- Framework: FastAPI (async-ready, OpenAPI built-in)
- Storage: in-memory now; Postgres via SQLAlchemy when persistence is needed
- Tests: pytest + FastAPI TestClient

## Architecture (mermaid)
```mermaid
flowchart LR
    Client -->|HTTP/JSON| API[FastAPI app/main.py]
    API --> Service[TaskService app/service.py]
    Service --> Store[(in-memory dict)]
```
Business logic lives in a framework-free `TaskService` so it is unit-testable in
isolation; `app/main.py` is a thin HTTP adapter.

## API Specification
```yaml
openapi: 3.0.3
info:
  title: Task API
  version: 1.0.0
paths:
  /health:
    get:
      responses: { "200": { description: ok } }
  /tasks:
    get:
      responses: { "200": { description: list of tasks } }
    post:
      responses: { "201": { description: created }, "400": { description: invalid } }
  /tasks/{task_id}:
    get:
      responses: { "200": { description: task }, "404": { description: missing } }
    delete:
      responses: { "204": { description: deleted }, "404": { description: missing } }
  /tasks/{task_id}/complete:
    post:
      responses: { "200": { description: completed }, "404": { description: missing } }
```

## Data Schema (future persistence)
```sql
CREATE TABLE tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);
```
"""

_QA_PLAN = """\
# Test Plan — Task API

## Test Cases (from acceptance criteria)
- TC-1 Create task -> 201, done=false (US-1)
- TC-2 Create with empty/whitespace title -> 400 (edge)
- TC-3 List returns created tasks (US-2)
- TC-4 Complete task -> done=true (US-3)
- TC-5 Complete/get/delete missing task -> 404 (edge)
- TC-6 Delete task -> 204, subsequent get -> 404 (US-4)

## Edge Cases
- Empty title, whitespace-only title.
- Operating on non-existent IDs.
- Double-complete (idempotent), double-delete (404).

## Performance / Load (sketch)
- 200 concurrent clients creating+listing for 60s; p95 < 200ms; 0 errors.
- Tool: locust or k6 against the deployed Staging service.
"""


def canned_response(role: str, prompt: str) -> str:
    """Return a deterministic artifact for a role in dry-run mode."""
    if role == "product_manager":
        return _PM_DOC
    if role == "ux_designer":
        return _UX_DOC
    if role == "tech_lead_design":
        return _TL_DOC
    if role == "tech_lead_review":
        return (
            "REVIEW_STATUS: approve\n\n"
            "# Code Review\n"
            "- Business logic is cleanly separated from the web layer (good testability).\n"
            "- Input validation rejects empty titles; 404s handled.\n"
            "- Unit tests cover create/get/complete/delete and error paths.\n"
            "Approved to proceed to CI."
        )
    if role == "qa_planning":
        return _QA_PLAN
    if role in ("software_engineer", "software_engineer_fix"):
        return file_blocks(SWE_FILES)
    if role == "qa_engineer":
        return file_blocks(QA_FILES)
    if role == "devops_ci":
        return file_blocks(CI_FILES)
    if role == "devops_cd":
        return file_blocks(CD_FILES)
    if role == "operate":
        return file_blocks(OPERATE_FILES)
    return f"[dry-run stub for role={role}]"
