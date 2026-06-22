"""🚀 DevOps / SRE.

Builds and runs the platform: containerisation + CI in the build phase, CD + IaC + K8s
in the deploy phase, and monitoring/alerting + a runbook in the operate phase. The
operate node also simulates a post-deploy health check and rolls the loop forward with
a product-metrics summary feeding the next cycle.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem, security
from ..state import TeamState
from .base import (
    emit_files,
    feature_brief,
    generate,
    output_dir,
    relpath,
    stack_hint,
    with_skills,
)

ROLE = "devops_sre"

CI_SYSTEM = """You are a DevOps engineer practising DevSecOps. Produce a hardened Dockerfile
and a GitHub Actions CI workflow:
- Dockerfile — pin a slim base image (no `:latest`), run as a non-root `USER`, add a
  `HEALTHCHECK`, and bake in no secrets.
- .github/workflows/ci.yml — runs on `pull_request` and `push` to `main`, with jobs that
  install deps, lint, and run the project's test suite, plus security jobs that shift
  security left: a SAST scan (e.g. Semgrep/Bandit), a dependency scan appropriate to the
  stack (e.g. pip-audit / npm audit / govulncheck), and a Trivy image+config scan that
  fails on HIGH/CRITICAL. Read any secrets from `${{ secrets.* }}`, set least-privilege
  `permissions:`, pin actions to a version, and cache dependencies.
The CI workflow is the pull-request gate: a red job blocks the merge (make the checks
branch-protection rules). Emit files as <<<FILE path >>> ... <<<END>>> blocks, no markdown
fences."""

CD_SYSTEM = """You are an SRE practising DevSecOps. Add a GitHub Actions deploy workflow,
plus Terraform and Kubernetes manifests:
- .github/workflows/cd.yml — triggers on `push` to `main` (and `workflow_dispatch`); gate
  production behind an `environment:` with required reviewers. Build the image once,
  generate (and optionally sign) an SBOM, then deploy with a safe rollout (canary or
  blue-green) and an automatic rollback step (`if: failure()`) on a failed health check.
- terraform/main.tf — Infrastructure as Code.
- k8s/deployment.yaml and k8s/service.yaml — a readiness probe and a hardened pod/container
  securityContext (runAsNonRoot, allowPrivilegeEscalation: false, capabilities drop ALL,
  readOnlyRootFilesystem) plus CPU/memory requests and limits.
Promote the same image artifact through staging to production. Emit files as
<<<FILE path >>> ... <<<END>>> blocks, no markdown fences."""

OPERATE_SYSTEM = """You are an SRE setting up observability. Produce Prometheus scrape
config (monitoring/prometheus.yml), alert rules for error-rate and latency
(monitoring/alerts.yml), and an on-call runbook with disaster-recovery steps
(docs/runbook.md). Emit files as <<<FILE path >>> ... <<<END>>> blocks, no fences."""

DOCS_SYSTEM = """You are a DevOps/SRE engineer documenting the infrastructure for on-call
and platform engineers. Explain where and how the service is deployed: how the GitHub
Actions CI and CD workflows fit together (CI gates the pull request; CD builds and deploys
on `main` behind an environment approval), what each job does, the container image, the
Terraform-managed cloud resources, the Kubernetes Deployment and Service, the required
environment variables / GitHub Actions secrets and where they are stored (never secrets in
git), and the rollout/rollback strategy. Output GitHub-flavoured markdown only (no file
blocks)."""


async def devops_ci_node(state: TeamState) -> TeamState:
    """Containerise the service and wire up the CI workflow."""
    ui.announce(
        ROLE,
        "code",
        "Containerising and wiring up GitHub Actions CI with security scans",
        [
            "containerize-service",
            "build-ci-pipeline",
            "ci-cd-and-automation",
            "github-actions-expert",
            "container-hardening",
            "sast-scanning",
            "dependency-scanning",
            "vulnerability-scanning",
        ],
    )
    stack = stack_hint(state) or "the application"
    files = await emit_files(
        state,
        model_role="devops_ci",
        character=ROLE,
        system_prompt=CI_SYSTEM,
        user_prompt=(
            f"Containerise this {stack} service and set up CI with GitHub Actions. Provide a "
            "Dockerfile suited to the stack (correct base image plus build and run commands "
            "for it) and a .github/workflows/ci.yml that installs deps, lints, runs the test "
            "suite, and runs the SAST, dependency, and image security scans."
        )
        + feature_brief(state),
        research_queries=[
            "latest GitHub Actions workflow syntax and jobs 2026",
            "GitHub Actions CI lint test python best practices 2026",
            "GitHub Actions Trivy SAST dependency scan security gate 2026",
            f"latest official Docker base image tags for {stack} 2026",
        ],
    )
    return {
        "dockerfile": files.get("Dockerfile", ""),
        "ci_config": files.get(".github/workflows/ci.yml", ""),
        "ci_workflow": files.get(".github/workflows/ci.yml", ""),
        "source_files": files,
        "current_phase": "code",
    }


async def devops_cd_node(state: TeamState) -> TeamState:
    """Set up continuous deployment, IaC, and Kubernetes manifests."""
    ui.announce(
        ROLE,
        "deploy",
        "Building GitHub Actions CD workflow, IaC and hardened Kubernetes manifests",
        [
            "build-cd-pipeline",
            "github-actions-expert",
            "write-infrastructure-code",
            "write-k8s-manifests",
            "kubernetes-hardening",
            "sbom-supply-chain",
        ],
    )
    files = await emit_files(
        state,
        model_role="devops_cd",
        character=ROLE,
        system_prompt=CD_SYSTEM,
        user_prompt=(
            "Set up continuous deployment for the containerised service: add a "
            ".github/workflows/cd.yml that builds the image, generates an SBOM, and deploys "
            "on `main` behind an environment approval with a safe rollout (canary or "
            "blue-green) and automatic rollback, plus Terraform and Kubernetes manifests "
            "(deployment with readiness probe, service)."
        )
        + feature_brief(state),
        research_queries=[
            "GitHub Actions deploy environment required reviewers approval 2026",
            "GitHub Actions canary blue-green deploy kubernetes with rollback 2026",
            "latest Kubernetes Deployment and Service apiVersion 2026",
            "current Terraform syntax and best practices 2026",
        ],
    )
    return {
        "cd_config": files.get(".github/workflows/cd.yml", ""),
        "cd_workflow": files.get(".github/workflows/cd.yml", ""),
        "iac": files.get("terraform/main.tf", ""),
        "k8s": "\n".join(content for path, content in files.items() if path.startswith("k8s/")),
        "source_files": files,
        "current_phase": "deploy",
    }


async def operate_node(state: TeamState) -> TeamState:
    """Stand up observability and a runbook, then run a simulated post-deploy health check."""
    ui.announce(
        ROLE,
        "operate",
        "Standing up monitoring, alerts and a runbook; running a post-deploy health check",
        ["configure-observability", "write-runbook"],
    )
    files = await emit_files(
        state,
        model_role="operate",
        character=ROLE,
        system_prompt=OPERATE_SYSTEM,
        user_prompt=(
            "Set up observability for the deployed Task API: Prometheus config, alert rules "
            "(error rate, latency), and an on-call runbook with DR steps."
        )
        + feature_brief(state),
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


async def devops_docs_node(state: TeamState) -> TeamState:
    """Document the infrastructure and run a DevSecOps audit of the deployment artifacts."""
    ui.announce(
        ROLE,
        "document",
        "Documenting infrastructure and auditing deployment security",
        ["document-infrastructure", "audit-container-security"],
    )

    # Deterministic, offline DevSecOps review of the artifacts produced earlier in the run.
    security_review = security.audit_report(
        dockerfile=state.get("dockerfile", ""),
        k8s=state.get("k8s", ""),
        ci_config=state.get("ci_workflow", ""),
        pipeline=state.get("cd_workflow", ""),
    )
    review_path = filesystem.write_doc(output_dir(state), "security_review.md", security_review)
    ui.written(relpath(state, [review_path]))

    user = (
        "Document the infrastructure and deployment for this service. Cover the GitHub "
        "Actions CI and CD workflows, the container image, the Terraform resources, the "
        "Kubernetes manifests, the required environment variables / GitHub Actions secrets "
        "and where they live, and the rollout/rollback strategy.\n\n"
        f"### GitHub Actions CI (.github/workflows/ci.yml)\n{state.get('ci_workflow', '')}\n\n"
        f"### GitHub Actions CD (.github/workflows/cd.yml)\n{state.get('cd_workflow', '')}\n\n"
        f"### Dockerfile\n{state.get('dockerfile', '')}\n\n"
        f"### Terraform\n{state.get('iac', '')}\n\n"
        f"### Kubernetes\n{state.get('k8s', '')}\n"
    ) + feature_brief(state)
    doc = await generate(
        "devops_docs",
        with_skills(DOCS_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "GitHub Actions CI/CD documentation best practices 2026",
            "latest infrastructure documentation and deployment runbook best practices 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "infrastructure.md", doc)
    ui.written(relpath(state, [path]))
    return {
        "infrastructure_docs": doc,
        "security_review": security_review,
        "current_phase": "document",
    }
