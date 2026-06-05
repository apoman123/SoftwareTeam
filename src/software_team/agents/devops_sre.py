"""🚀 DevOps / SRE.

Builds and runs the platform: containerisation + CI in the build phase, CD + IaC + K8s
in the deploy phase, and monitoring/alerting + a runbook in the operate phase. The
operate node also simulates a post-deploy health check and rolls the loop forward with
a product-metrics summary feeding the next cycle.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..state import TeamState
from .base import emit_files, output_dir, relpath

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


def devops_ci_node(state: TeamState) -> TeamState:
    """Containerise the service and wire up the CI workflow."""
    ui.announce(
        ROLE,
        "code",
        "Containerising and wiring up CI",
        ["containerize-service", "build-ci-pipeline"],
    )
    files = emit_files(
        state,
        model_role="devops_ci",
        character=ROLE,
        system_prompt=CI_SYSTEM,
        user_prompt=(
            "Containerise this Python service and set up CI. The app runs with "
            "`uvicorn app.main:app`. Provide Dockerfile and .github/workflows/ci.yml."
        ),
        research_queries=[
            "latest GitHub Actions workflow syntax and current action versions 2026",
            "latest official Python Docker base image tags 2026",
        ],
    )
    return {
        "dockerfile": files.get("Dockerfile", ""),
        "ci_config": files.get(".github/workflows/ci.yml", ""),
        "source_files": files,
        "current_phase": "code",
    }


def devops_cd_node(state: TeamState) -> TeamState:
    """Set up continuous deployment, IaC, and Kubernetes manifests."""
    ui.announce(
        ROLE,
        "deploy",
        "Building CD pipeline, IaC and Kubernetes manifests",
        ["build-cd-pipeline", "write-infrastructure-code", "write-k8s-manifests"],
    )
    files = emit_files(
        state,
        model_role="devops_cd",
        character=ROLE,
        system_prompt=CD_SYSTEM,
        user_prompt=(
            "Set up continuous deployment for the containerised service with a safe rollout, "
            "Terraform, and Kubernetes manifests (deployment with readiness probe, service)."
        ),
        research_queries=[
            "latest Kubernetes Deployment and Service apiVersion 2026",
            "current Terraform syntax and best practices 2026",
        ],
    )
    return {
        "cd_config": files.get(".github/workflows/cd.yml", ""),
        "iac": files.get("terraform/main.tf", ""),
        "k8s": "\n".join(content for path, content in files.items() if path.startswith("k8s/")),
        "source_files": files,
        "current_phase": "deploy",
    }


def operate_node(state: TeamState) -> TeamState:
    """Stand up observability and a runbook, then run a simulated post-deploy health check."""
    ui.announce(
        ROLE,
        "operate",
        "Standing up monitoring, alerts and a runbook; running a post-deploy health check",
        ["configure-observability", "write-runbook"],
    )
    files = emit_files(
        state,
        model_role="operate",
        character=ROLE,
        system_prompt=OPERATE_SYSTEM,
        user_prompt=(
            "Set up observability for the deployed Task API: Prometheus config, alert rules "
            "(error rate, latency), and an on-call runbook with DR steps."
        ),
        research_queries=[
            "latest Prometheus scrape config and alerting rule syntax 2026",
        ],
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
    path = filesystem.write_doc(output_dir(state), "operations_report.md", ops_report)
    ui.written(relpath(state, [path]))
    ui.note(f"post-deploy status: [bold]{deploy_status}[/bold]")

    return {
        "monitoring": "\n".join(
            content for name, content in files.items() if name.startswith("monitoring/")
        ),
        "runbook": files.get("docs/runbook.md", ""),
        "source_files": files,
        "deploy_status": deploy_status,
        "ops_report": ops_report,
        "current_phase": "operate",
    }
