"""🚀 DevOps / SRE.

Builds and runs the platform: containerisation + CI in the build phase, CD + IaC + K8s
in the deploy phase, and monitoring/alerting + a runbook in the operate phase. The
operate node also simulates a post-deploy health check and rolls the loop forward with
a product-metrics summary feeding the next cycle.
"""

from __future__ import annotations

from .. import ui
from ..skills import filesystem
from ..skills.authoring import parse_file_blocks
from ..skills.registry import skill_names
from .base import generate, output_dir, relpath

ROLE = "devops_sre"

CI_SYSTEM = """You are a DevOps engineer. Produce a Dockerfile and a GitHub Actions CI
workflow (.github/workflows/ci.yml) that installs deps, lints and runs pytest on pull
requests. Emit files as <<<FILE path >>> ... <<<END>>> blocks, no markdown fences."""

CD_SYSTEM = """You are an SRE. Produce a GitHub Actions CD workflow
(.github/workflows/cd.yml) that builds an image and deploys with a safe rollout
(canary or blue-green), plus Terraform (terraform/main.tf) and Kubernetes manifests
(k8s/deployment.yaml with a readiness probe, k8s/service.yaml). Emit files as
<<<FILE path >>> ... <<<END>>> blocks, no markdown fences."""

OPERATE_SYSTEM = """You are an SRE setting up observability. Produce Prometheus scrape
config (monitoring/prometheus.yml), alert rules for error-rate and latency
(monitoring/alerts.yml), and an on-call runbook with disaster-recovery steps
(docs/runbook.md). Emit files as <<<FILE path >>> ... <<<END>>> blocks, no fences."""


def _emit(state: dict, role: str, system: str, user: str) -> dict[str, str]:
    text = generate(role, system, user, state)
    files = parse_file_blocks(text)
    if files:
        ui.written(relpath(state, filesystem.write_files(output_dir(state), files)))
    else:
        ui.note("[yellow]no file blocks parsed[/yellow]")
    return files


def devops_ci_node(state: dict) -> dict:
    ui.announce(ROLE, "code", "Containerising and wiring up CI", ["write_dockerfile", "generate_ci_pipeline"])
    files = _emit(
        state, "devops_ci", CI_SYSTEM,
        "Containerise this Python service and set up CI. The app runs with "
        "`uvicorn app.main:app`. Provide Dockerfile and .github/workflows/ci.yml.",
    )
    return {
        "dockerfile": files.get("Dockerfile", ""),
        "ci_config": files.get(".github/workflows/ci.yml", ""),
        "source_files": files,
        "current_phase": "code",
    }


def devops_cd_node(state: dict) -> dict:
    ui.announce(
        ROLE, "deploy",
        "Building CD pipeline, IaC and Kubernetes manifests",
        ["generate_cd_pipeline", "write_terraform", "write_k8s_manifests"],
    )
    files = _emit(
        state, "devops_cd", CD_SYSTEM,
        "Set up continuous deployment for the containerised service with a safe rollout, "
        "Terraform, and Kubernetes manifests (deployment with readiness probe, service).",
    )
    return {
        "cd_config": files.get(".github/workflows/cd.yml", ""),
        "iac": files.get("terraform/main.tf", ""),
        "k8s": "\n".join(c for p, c in files.items() if p.startswith("k8s/")),
        "source_files": files,
        "current_phase": "deploy",
    }


def operate_node(state: dict) -> dict:
    ui.announce(
        ROLE, "operate",
        "Standing up monitoring, alerts and a runbook; running a post-deploy health check",
        ["write_monitoring_config", "write_runbook"],
    )
    files = _emit(
        state, "operate", OPERATE_SYSTEM,
        "Set up observability for the deployed Task API: Prometheus config, alert rules "
        "(error rate, latency), and an on-call runbook with DR steps.",
    )

    # Simulate a post-deploy health check + product metrics for the next cycle (PM input).
    healthy = state.get("tests_passed", False)
    deploy_status = "healthy" if healthy else "degraded — investigate before promoting"
    ops_report = (
        "# Operations Report\n\n"
        f"- Deploy health: **{deploy_status}**\n"
        f"- Tests passed before release: **{state.get('tests_passed', False)}**\n"
        f"- Review iterations: {state.get('review_iters', 0)}, "
        f"bug-fix iterations: {state.get('fix_iters', 0)}\n"
        "- Monitoring: Prometheus + alert rules active; on-call runbook published.\n\n"
        "## PM: next-cycle backlog candidates\n"
        "- Add persistence (Postgres) so tasks survive restarts.\n"
        "- Add authentication for multi-user support.\n"
        "- Instrument real `/metrics` endpoint for the dashboards above.\n"
    )
    out = output_dir(state)
    path = filesystem.write_doc(out, "operations_report.md", ops_report)
    ui.written(relpath(state, [path]))
    ui.note(f"post-deploy status: [bold]{deploy_status}[/bold]")

    return {
        "monitoring": "\n".join(c for p, c in files.items() if p.startswith("monitoring/")),
        "runbook": files.get("docs/runbook.md", ""),
        "source_files": files,
        "deploy_status": deploy_status,
        "ops_report": ops_report,
        "current_phase": "operate",
    }
