"""Canned, deterministic artifacts for `--dry-run` mode.

These let the whole graph + file generation be verified with no Ollama server. The
software-engineer output is a real, runnable FastAPI "Task API" whose pure-logic unit
tests pass with only pytest installed (the FastAPI E2E tests `importorskip` if FastAPI
isn't present). Live mode replaces all of this with actual model generations.
"""

from __future__ import annotations

from .skills.common.authoring import delete_blocks, file_blocks
from .state import FEATURE_BRIEF_HEADER, FEATURE_OP_MARKERS, OP_GC, OP_REMOVE

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
# Incremental feature (dry-run): "add task priority"
#
# Demonstrates `software-team feature` deterministically: the engineer re-emits the two
# files it changes (service + web layer) and adds one new test file, extending the Task API
# with a priority field + a `POST /tasks/{id}/priority` endpoint. The new fields default,
# so the original unit and E2E tests still pass — i.e. the feature is integrated, not
# bolted on. Live mode replaces this with a real generation for the requested feature.
# --------------------------------------------------------------------------- #

_FEATURE_SERVICE_PY = '''\
"""In-memory Task service: pure business logic, no web framework required."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count

# Allowed task priorities, lowest to highest.
PRIORITIES = ("low", "medium", "high")


class TaskError(Exception):
    """Invalid task operation (e.g. bad input)."""


class TaskNotFound(TaskError):
    """Requested task does not exist."""


@dataclass
class Task:
    id: int
    title: str
    done: bool = False
    priority: str = "medium"


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._ids = count(1)

    def create(self, title: str, priority: str = "medium") -> Task:
        title = (title or "").strip()
        if not title:
            raise TaskError("title must not be empty")
        priority = self._validate_priority(priority)
        task = Task(id=next(self._ids), title=title, priority=priority)
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

    def set_priority(self, task_id: int, priority: str) -> Task:
        task = self.get(task_id)
        task.priority = self._validate_priority(priority)
        return task

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        del self._tasks[task_id]

    @staticmethod
    def _validate_priority(priority: str) -> str:
        priority = (priority or "").strip().lower()
        if priority not in PRIORITIES:
            raise TaskError(f"priority must be one of {PRIORITIES}")
        return priority
'''

_FEATURE_MAIN_PY = '''\
"""FastAPI wiring over the pure TaskService."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .service import TaskError, TaskNotFound, TaskService

app = FastAPI(title="Task API", version="1.1.0")
service = TaskService()


class TaskIn(BaseModel):
    title: str
    priority: str = "medium"


class PriorityIn(BaseModel):
    priority: str


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool
    priority: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskIn) -> TaskOut:
    try:
        task = service.create(payload.title, payload.priority)
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


@app.post("/tasks/{task_id}/priority", response_model=TaskOut)
def set_task_priority(task_id: int, payload: PriorityIn) -> TaskOut:
    try:
        task = service.set_priority(task_id, payload.priority)
    except TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except TaskError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TaskOut(**task.__dict__)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    try:
        service.delete(task_id)
    except TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
'''

_FEATURE_TESTS = '''\
"""Unit tests for the task-priority feature."""
import pytest

from app.service import PRIORITIES, TaskError, TaskService


def test_create_defaults_to_medium_priority():
    svc = TaskService()
    assert svc.create("write tests").priority == "medium"


def test_create_with_explicit_priority():
    svc = TaskService()
    assert svc.create("ship it", "high").priority == "high"


def test_set_priority_updates_task():
    svc = TaskService()
    task = svc.create("triage")
    assert svc.set_priority(task.id, "low").priority == "low"


def test_invalid_priority_rejected():
    svc = TaskService()
    task = svc.create("triage")
    with pytest.raises(TaskError):
        svc.set_priority(task.id, "urgent")


def test_priorities_are_ordered_low_to_high():
    assert PRIORITIES == ("low", "medium", "high")
'''

FEATURE_FILES = {
    "app/service.py": _FEATURE_SERVICE_PY,
    "app/main.py": _FEATURE_MAIN_PY,
    "tests/test_priority.py": _FEATURE_TESTS,
}

# --------------------------------------------------------------------------- #
# Incremental removal (dry-run): "remove the task priority feature"
#
# Demonstrates `software-team remove` deterministically: the engineer re-emits the two
# files it trims back to their pre-feature form and emits a deletion directive for the
# feature's now-orphaned test file — proving a feature is genuinely taken out (its file is
# deleted, not just left empty), while every other feature keeps passing. Live mode replaces
# this with a real generation for the feature the user asked to remove.
# --------------------------------------------------------------------------- #

REMOVE_REEMIT = {"app/service.py": _SERVICE_PY, "app/main.py": _MAIN_PY}
REMOVE_DELETES = ("tests/test_priority.py",)

# --------------------------------------------------------------------------- #
# Garbage-collection clean-up (dry-run)
#
# The GC fix is a behaviour-preserving re-emit of the service module, so the canned project's
# tests still pass while the loop exercises scan → request → fix → verify. Live mode replaces
# this with a real clean-up of whatever the scanner reported.
# --------------------------------------------------------------------------- #

GC_FIX_REEMIT = {"app/service.py": _SERVICE_PY}

_GC_REQUEST_DOC = """\
# Garbage-Collection Fix Request

Prioritised clean-up for the engineer. Keep behaviour unchanged; all tests must stay green.

1. **Reconcile the docs with the code** — update any documentation that references files that
   no longer exist, and document modules that are undocumented.
2. **Restore layering** — move any delivery-framework code out of pure-logic modules into the
   thin adapter.
3. **Clear technical debt** — resolve `TODO`/`FIXME` markers, replace bare exception handlers
   with specific handling, and remove leftover debug output.

Re-emit only the files you change; delete genuinely dead files.
"""

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
# Frontend (dry-run): a minimal React client for the Task API, under frontend/.
# Only emitted when triage decides the project needs a UI (needs_frontend).
# --------------------------------------------------------------------------- #

_FRONTEND_PACKAGE_JSON = """\
{
  "name": "task-app-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "vite": "^5.3.0",
    "vitest": "^2.0.0"
  }
}
"""

_FRONTEND_API_JS = """\
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function listTasks() {
  const res = await fetch(`${BASE_URL}/tasks`);
  if (!res.ok) throw new Error("Failed to load tasks");
  return res.json();
}

export async function addTask(title) {
  const res = await fetch(`${BASE_URL}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Title is required");
  return res.json();
}
"""

_FRONTEND_APP_JSX = """\
import { useEffect, useState } from "react";
import { addTask, listTasks } from "./api.js";

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    listTasks().then(setTasks).catch((e) => setError(e.message));
  }, []);

  async function onAdd(e) {
    e.preventDefault();
    try {
      const task = await addTask(title);
      setTasks((prev) => [...prev, task]);
      setTitle("");
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main>
      <h1>Tasks</h1>
      {tasks.length === 0 ? <p>No tasks yet — add your first one.</p> : null}
      <ul>
        {tasks.map((t) => (
          <li key={t.id}>{t.title}</li>
        ))}
      </ul>
      <form onSubmit={onAdd}>
        <label htmlFor="title">New task</label>
        <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <button type="submit">Add</button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
    </main>
  );
}
"""

_FRONTEND_TEST = """\
import { describe, expect, it } from "vitest";

describe("frontend smoke", () => {
  it("knows the empty-state copy", () => {
    expect("No tasks yet — add your first one.").toContain("No tasks yet");
  });
});
"""

FRONTEND_FILES = {
    "frontend/package.json": _FRONTEND_PACKAGE_JSON,
    "frontend/src/api.js": _FRONTEND_API_JS,
    "frontend/src/App.jsx": _FRONTEND_APP_JSX,
    "frontend/src/App.test.js": _FRONTEND_TEST,
}

# --------------------------------------------------------------------------- #
# DevOps / SRE artifacts
# --------------------------------------------------------------------------- #

CI_FILES = {
    # Hardened per DevSecOps practice: pinned slim base, non-root user, HEALTHCHECK,
    # no secrets baked into layers.
    "Dockerfile": """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --system --no-create-home appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    # GitLab CI/CD gates the merge request (lint + test), then hands off to Jenkins via the
    # remote build API. $JENKINS_URL / $JENKINS_TOKEN are masked GitLab CI/CD variables.
    ".gitlab-ci.yml": """\
stages:
  - lint
  - test
  - security
  - integrate

default:
  image: python:3.12-slim
  before_script:
    - pip install --no-cache-dir -r requirements.txt

lint:
  stage: lint
  script:
    - pip install ruff
    - ruff check .

test:
  stage: test
  script:
    - pytest -q

# DevSecOps: shift security left — SAST, dependency scan, and image/config CVE scan gate
# the merge request before it can trigger the heavier Jenkins build.
sast:
  stage: security
  script:
    - pip install bandit
    - bandit -r app -ll

dependency-scan:
  stage: security
  script:
    - pip install pip-audit
    - pip-audit -r requirements.txt

container-scan:
  stage: security
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  before_script: []
  script:
    - trivy config --exit-code 1 --severity HIGH,CRITICAL .
    - trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed task-api:$CI_COMMIT_SHA

trigger-jenkins:
  stage: integrate
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'
  script:
    - >
      curl --fail -X POST
      "$JENKINS_URL/job/task-api/buildWithParameters?token=$JENKINS_TOKEN&ref=$CI_COMMIT_REF_NAME&sha=$CI_COMMIT_SHA"
""",
    # Jenkins runs the heavier build; secrets come from the Jenkins credential store.
    "Jenkinsfile": """\
pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Install') {
      steps {
        sh 'pip install --no-cache-dir -r requirements.txt'
      }
    }
    stage('Quality') {
      parallel {
        stage('Lint') {
          steps {
            sh 'pip install ruff && ruff check .'
          }
        }
        stage('Test') {
          steps {
            sh 'pytest -q'
          }
        }
      }
    }
  }
  post {
    success {
      echo 'CI green — reporting success back to the GitLab merge request.'
    }
    failure {
      echo 'CI failed — blocking the merge request.'
    }
  }
}
""",
}

CD_FILES = {
    # The full GitLab pipeline: the CI stages plus a manual production deploy that triggers
    # the Jenkins deploy job (canary rollout). Same image artifact is promoted through.
    ".gitlab-ci.yml": """\
stages:
  - lint
  - test
  - security
  - integrate
  - deploy

default:
  image: python:3.12-slim
  before_script:
    - pip install --no-cache-dir -r requirements.txt

lint:
  stage: lint
  script:
    - pip install ruff
    - ruff check .

test:
  stage: test
  script:
    - pytest -q

# DevSecOps: SAST + dependency scan + image/config CVE scan + SBOM gate the pipeline.
sast:
  stage: security
  script:
    - pip install bandit
    - bandit -r app -ll

dependency-scan:
  stage: security
  script:
    - pip install pip-audit
    - pip-audit -r requirements.txt

container-scan:
  stage: security
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  before_script: []
  script:
    - trivy config --exit-code 1 --severity HIGH,CRITICAL .
    - trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed task-api:$CI_COMMIT_SHA

sbom:
  stage: security
  image:
    name: anchore/syft:latest
    entrypoint: [""]
  before_script: []
  script:
    - syft task-api:$CI_COMMIT_SHA -o cyclonedx-json > sbom.json
  artifacts:
    paths:
      - sbom.json

trigger-jenkins:
  stage: integrate
  script:
    - >
      curl --fail -X POST
      "$JENKINS_URL/job/task-api/buildWithParameters?token=$JENKINS_TOKEN&ref=$CI_COMMIT_REF_NAME&sha=$CI_COMMIT_SHA"

deploy-production:
  stage: deploy
  environment:
    name: production
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
  script:
    - >
      curl --fail -X POST
      "$JENKINS_URL/job/task-api-deploy/buildWithParameters?token=$JENKINS_TOKEN&sha=$CI_COMMIT_SHA&strategy=canary"
""",
    # Jenkins owns build + deploy with a safe rollout and an automatic rollback on failure.
    "Jenkinsfile": """\
pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  environment {
    IMAGE = "task-api:${env.GIT_COMMIT}"
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Build image') {
      steps {
        withCredentials([usernamePassword(
            credentialsId: 'registry',
            usernameVariable: 'REG_USER',
            passwordVariable: 'REG_PASS')]) {
          sh 'docker build -t $IMAGE .'
        }
      }
    }
    stage('Deploy (canary -> full)') {
      steps {
        sh 'kubectl set image deploy/task-api task-api=$IMAGE -n task-api'
        sh 'kubectl rollout status deploy/task-api -n task-api --timeout=120s'
      }
    }
  }
  post {
    failure {
      echo 'Health check failed — rolling back.'
      sh 'kubectl rollout undo deploy/task-api -n task-api'
    }
  }
}
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
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: task-api
          image: task-api:1.0.0
          ports:
            - containerPort: 8000
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
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

## Feature Plan
1. Task creation and retrieval (US-1, US-2) — create a task and list/fetch tasks.
2. Task completion and deletion (US-3, US-4) — mark a task done and delete a task.
"""

_UX_DOC = """\
# UX — Task API (API-first, minimal console client)

## User Flow
1. User lists tasks -> sees outstanding items.
2. User adds a task -> item appears with done=false.
3. User completes a task -> item shows done=true.
4. User deletes a task -> item disappears.

## Screen & Layout Description
- Task list (single screen). A title header ("Tasks") sits at the top. The main region is
  the list of tasks, one row per task showing a done indicator, the title, and complete
  and delete actions. The primary action is the "add task" input with its Add button, kept
  at the bottom of the list. On narrow widths the per-row actions stack beneath the title.

## Component & State Specs
- Add field: validates on blur; an empty or whitespace-only title is rejected with the
  inline message "Title is required" (default / focus / error states).
- Task list: empty state reads "No tasks yet — add your first one."; each row has default
  and completed states.
- Errors: 400 (empty title) and 404 (missing task) surface as an inline error message
  with a clear recovery path, never colour alone.

## Usability & Accessibility Notes
- Visible labels on the input; every control is keyboard-operable with a visible focus ring.
- Done state is conveyed by both the indicator and text, not colour alone (WCAG POUR).
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

# --------------------------------------------------------------------------- #
# Document & Handoff deliverables
# --------------------------------------------------------------------------- #

_README_DOC = """\
# Task API

A small HTTP service for tracking tasks: create, list, complete, and delete them.
Business logic lives in a framework-free `TaskService`; `app/main.py` is a thin FastAPI
adapter over it.

## Prerequisites
- Python 3.12+
- `pip` (or `uv`)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload    # serves on http://127.0.0.1:8000
```
Interactive API docs are then available at `http://127.0.0.1:8000/docs`.

## Usage
```bash
# Health check
curl http://127.0.0.1:8000/health

# Create a task
curl -X POST http://127.0.0.1:8000/tasks -H 'Content-Type: application/json' \\
  -d '{"title": "buy milk"}'

# List tasks
curl http://127.0.0.1:8000/tasks

# Complete / delete a task
curl -X POST http://127.0.0.1:8000/tasks/1/complete
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

## Tests
```bash
pip install -r requirements.txt
pytest -q
```
"""

_INFRA_DOC = """\
# Infrastructure & Deployment — Task API

Where and how the service runs, for on-call and platform engineers. Pair this with the
[on-call runbook](runbook.md), which covers what to do when an alert fires.

## Pipelines (GitLab CI integrated with Jenkins)
- **GitLab CI** (`.gitlab-ci.yml`) — on every merge request: install deps, lint, and run
  `pytest`. A green pipeline gates merges to `main`. Its final `trigger-jenkins` job calls
  Jenkins' remote build API (`$JENKINS_URL` / `$JENKINS_TOKEN` are masked CI/CD variables),
  and a manual `deploy-production` job triggers the Jenkins deploy job on `main`.
- **Jenkins** (`Jenkinsfile`) — a Declarative pipeline that runs the heavier build and
  deploy: build the image, roll it out (canary → full), and automatically roll back on a
  failed health check. Secrets come from the Jenkins credential store, never git.

## Container image
- Built from `python:3.12-slim` (see `Dockerfile`); started with
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## Cloud resources (Terraform)
- `terraform/main.tf` provisions the `task-api` Kubernetes namespace and providers.
- Apply with `terraform init && terraform apply`.

## Kubernetes
- `k8s/deployment.yaml` — 2 replicas with a `/health` readiness probe.
- `k8s/service.yaml` — ClusterIP service on port 80 → container port 8000.

## Configuration
| Variable | Where it lives | Purpose |
|----------|----------------|---------|
| `CI_COMMIT_SHA` | GitLab CI (built-in) | Image version/tag to deploy |
| `JENKINS_URL` / `JENKINS_TOKEN` | GitLab CI/CD variables (masked) | Trigger the Jenkins job |
| Registry / cloud creds | Jenkins credential store (never git) | Push images, deploy |

## Rollout & rollback
- **Rollout:** canary first, then promote to full once healthy.
- **Rollback:** `kubectl rollout undo deploy/task-api -n task-api`.
"""

_TEST_REPORT = """\
# Test Report — Task API

## Coverage
| Test case | Maps to | Type |
|-----------|---------|------|
| TC-1 create → 201 | US-1 | unit + e2e |
| TC-2 empty title → 400 | edge | unit + e2e |
| TC-3 list tasks | US-2 | e2e |
| TC-4 complete → done | US-3 | unit + e2e |
| TC-5 missing id → 404 | edge | unit + e2e |
| TC-6 delete → 204 | US-4 | e2e |

## Results
- **Status: PASS.** Unit tests (`tests/test_service.py`) and end-to-end tests
  (`tests/test_e2e.py`) all green on the latest run.
- Reproduce: `pip install -r requirements.txt && pytest -q`.

## Residual risk
- No persistence yet — state is in-memory and lost on restart (not under test).
- Performance/load scenario is sketched but not yet executed.
- No authentication, so multi-user isolation is out of scope for this release.
"""

_USER_MANUAL = """\
# User Manual — Task API

A guide to using the Task API to keep track of your to-dos.

## Creating a task
Send the title of what you want to remember; the task starts as *not done*.
Empty titles are rejected so your list stays meaningful.

## Viewing your tasks
List all tasks to see everything outstanding, with each task's title and whether it is done.

## Completing a task
Mark a task complete when you finish it; it then shows as done.

## Deleting a task
Remove a task you no longer need. Deleting something that is already gone reports "not found".

## Release Notes

### v1.0.0
**Added**
- Create a task with a title (US-1).
- List all tasks (US-2).
- Mark a task complete (US-3).
- Delete a task (US-4).

**Changed**
- Empty or whitespace-only titles are now rejected with a clear error.

**Fixed**
- Acting on a missing task now returns a clear "not found" instead of a generic error.
"""


_SPEC_DOC = """\
# Spec: Task API

## Background
A small backend service that lets a single user manage a personal task list, consumed by a
thin client over an HTTP/JSON API. Generated by the interactive spec interview.

## Use cases
1. **Add a task** — provide a title, get back a task with a unique id and a `done` flag
   defaulting to false. Empty/whitespace titles are rejected.
2. **List tasks** — retrieve all tasks.
3. **View a task** — fetch a single task by id; unknown ids return not-found.
4. **Complete a task** — mark a task done.
5. **Delete a task** — remove a task; unknown ids return not-found.

## Functional requirements
- CRUD over tasks with input validation and clear, typed errors.
- Stable JSON contract suitable for a CLI or web client.

## Non-functional requirements
- Simple to run locally and to containerise.
- Reasonable latency under light load (p95 < 200ms).
- Clear errors (400 for bad input, 404 for missing resources).

## Technology
- Python + FastAPI for the service; pytest for tests (stated preference).

## Out of scope
- Authentication / multiple users.
- Durable persistence (in-memory storage is acceptable for v1).
"""


def canned_response(role: str, prompt: str) -> str:
    """Return a deterministic artifact for a role in dry-run mode."""
    if role == "spec_author":
        return _SPEC_DOC
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
    if role == "tech_lead_gc_request":
        return _GC_REQUEST_DOC
    if role in ("software_engineer", "software_engineer_fix"):
        # In a feature run the prompt carries the existing-software brief; re-emit only the
        # files the change touches so unchanged code is preserved by the merge reducer.
        if FEATURE_OP_MARKERS[OP_GC] in prompt:
            # Garbage-collection clean-up: a behaviour-preserving re-emit (tests stay green).
            return file_blocks(GC_FIX_REEMIT)
        if FEATURE_OP_MARKERS[OP_REMOVE] in prompt:
            # Remove: trim the two files back and delete the feature's orphaned test file.
            return file_blocks(REMOVE_REEMIT) + "\n\n" + delete_blocks(REMOVE_DELETES)
        if FEATURE_BRIEF_HEADER in prompt:
            return file_blocks(FEATURE_FILES)
        return file_blocks(SWE_FILES)
    if role == "frontend_engineer":
        return file_blocks(FRONTEND_FILES)
    if role == "qa_engineer":
        return file_blocks(QA_FILES)
    if role == "devops_ci":
        return file_blocks(CI_FILES)
    if role == "devops_cd":
        return file_blocks(CD_FILES)
    if role == "operate":
        return file_blocks(OPERATE_FILES)
    if role == "software_engineer_readme":
        return _README_DOC
    if role == "qa_report":
        return _TEST_REPORT
    if role == "devops_docs":
        return _INFRA_DOC
    if role == "product_manager_docs":
        return _USER_MANUAL
    return f"[dry-run stub for role={role}]"
