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
from .base import emit_files, feature_brief, generate, output_dir, relpath, with_skills

ROLE = "devops_sre"

CI_SYSTEM = """You are a DevOps engineer practising DevSecOps. Produce a hardened Dockerfile
and a GitLab CI/CD pipeline integrated with Jenkins:
- Dockerfile — pin a slim base image (no `:latest`), run as a non-root `USER`, add a
  `HEALTHCHECK`, and bake in no secrets.
- .gitlab-ci.yml — stages that install deps, lint and run pytest on merge requests, plus a
  `security` stage that shifts security left: a SAST scan (Bandit/Semgrep), a dependency
  scan (pip-audit), and a Trivy image+config scan that fails on HIGH/CRITICAL; then a final
  `trigger-jenkins` job that calls Jenkins' remote build API (buildWithParameters) using
  masked GitLab CI/CD variables ($JENKINS_URL, $JENKINS_TOKEN).
- Jenkinsfile — a Declarative pipeline (agent, stages: Checkout, Install, Lint, Test) that
  pulls secrets from the Jenkins credential store and reports status back to the GitLab MR.
GitLab CI owns the merge-request gate; Jenkins runs the heavier build. A red stage blocks
the merge. Emit files as <<<FILE path >>> ... <<<END>>> blocks, no markdown fences."""

CD_SYSTEM = """You are an SRE practising DevSecOps. Extend the GitLab + Jenkins CI/CD
pipeline with deployment, plus Terraform and Kubernetes manifests:
- .gitlab-ci.yml — add a `deploy` stage (manual gate to production) that triggers the
  Jenkins deploy job; keep the existing lint/test/security/trigger-jenkins stages.
- Jenkinsfile — add Build image and Deploy stages with a safe rollout (canary or
  blue-green) and an automatic rollback path on a failed health check; generate and sign an
  SBOM for the built image.
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
and platform engineers. Explain where and how the service is deployed: how the GitLab
CI/CD pipeline and the Jenkins pipeline fit together (GitLab gates the merge request and
triggers Jenkins for the heavier build/deploy), what each stage does, the container image,
the Terraform-managed cloud resources, the Kubernetes Deployment and Service, the required
environment variables / CI-CD variables / Jenkins credentials and where they are stored
(never secrets in git), and the rollout/rollback strategy. Output GitHub-flavoured
markdown only (no file blocks)."""


def devops_ci_node(state: TeamState) -> TeamState:
    """Containerise the service and wire up the CI workflow."""
    ui.announce(
        ROLE,
        "code",
        "Containerising and wiring up GitLab CI + Jenkins with security scans",
        [
            "containerize-service",
            "build-ci-pipeline",
            "ci-cd-and-automation",
            "jenkins-expert",
            "container-hardening",
            "sast-scanning",
            "dependency-scanning",
            "vulnerability-scanning",
        ],
    )
    files = emit_files(
        state,
        model_role="devops_ci",
        character=ROLE,
        system_prompt=CI_SYSTEM,
        user_prompt=(
            "Containerise this Python service and set up CI with GitLab integrated with "
            "Jenkins. The app runs with `uvicorn app.main:app`. Provide Dockerfile, "
            "a .gitlab-ci.yml that lints and tests then triggers Jenkins, and a Jenkinsfile."
        )
        + feature_brief(state),
        research_queries=[
            "latest GitLab CI/CD .gitlab-ci.yml syntax and stages 2026",
            "latest Jenkins declarative pipeline Jenkinsfile best practices 2026",
            "trigger Jenkins job from GitLab CI remote build API 2026",
            "latest official Python Docker base image tags 2026",
        ],
    )
    return {
        "dockerfile": files.get("Dockerfile", ""),
        "ci_config": files.get(".gitlab-ci.yml", ""),
        "gitlab_ci": files.get(".gitlab-ci.yml", ""),
        "jenkinsfile": files.get("Jenkinsfile", ""),
        "source_files": files,
        "current_phase": "code",
    }


def devops_cd_node(state: TeamState) -> TeamState:
    """Set up continuous deployment, IaC, and Kubernetes manifests."""
    ui.announce(
        ROLE,
        "deploy",
        "Building GitLab + Jenkins CD pipeline, IaC and hardened Kubernetes manifests",
        [
            "build-cd-pipeline",
            "jenkins-expert",
            "write-infrastructure-code",
            "write-k8s-manifests",
            "kubernetes-hardening",
            "sbom-supply-chain",
        ],
    )
    files = emit_files(
        state,
        model_role="devops_cd",
        character=ROLE,
        system_prompt=CD_SYSTEM,
        user_prompt=(
            "Set up continuous deployment for the containerised service: add a deploy stage "
            "to the GitLab pipeline that triggers the Jenkins deploy job with a safe rollout "
            "(canary or blue-green) and rollback, plus Terraform and Kubernetes manifests "
            "(deployment with readiness probe, service)."
        )
        + feature_brief(state),
        research_queries=[
            "latest GitLab CI manual deploy stage and environments 2026",
            "Jenkins declarative pipeline canary blue-green deploy with rollback 2026",
            "latest Kubernetes Deployment and Service apiVersion 2026",
            "current Terraform syntax and best practices 2026",
        ],
    )
    return {
        "cd_config": files.get(".gitlab-ci.yml", files.get("Jenkinsfile", "")),
        "gitlab_ci": files.get(".gitlab-ci.yml", ""),
        "jenkinsfile": files.get("Jenkinsfile", ""),
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


def devops_docs_node(state: TeamState) -> TeamState:
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
        ci_config=state.get("gitlab_ci", ""),
        pipeline=state.get("jenkinsfile", ""),
    )
    review_path = filesystem.write_doc(output_dir(state), "security_review.md", security_review)
    ui.written(relpath(state, [review_path]))

    user = (
        "Document the infrastructure and deployment for this service. Cover the GitLab CI/CD "
        "pipeline and how it integrates with Jenkins, the container image, the Terraform "
        "resources, the Kubernetes manifests, the required environment / CI-CD variables and "
        "Jenkins credentials and where they live, and the rollout/rollback strategy.\n\n"
        f"### GitLab CI/CD (.gitlab-ci.yml)\n{state.get('gitlab_ci', '')}\n\n"
        f"### Jenkins pipeline (Jenkinsfile)\n{state.get('jenkinsfile', '')}\n\n"
        f"### Dockerfile\n{state.get('dockerfile', '')}\n\n"
        f"### Terraform\n{state.get('iac', '')}\n\n"
        f"### Kubernetes\n{state.get('k8s', '')}\n"
    ) + feature_brief(state)
    doc = generate(
        "devops_docs",
        with_skills(DOCS_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "GitLab CI Jenkins integration documentation best practices 2026",
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
