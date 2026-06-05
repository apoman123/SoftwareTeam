---
name: build-ci-pipeline
description: Authors a GitLab CI pipeline (integrated with Jenkins) that gates every merge request. Use when automating integration.
---

# Build the CI pipeline

Author a **GitLab CI** pipeline (`.gitlab-ci.yml`) that runs on every merge request and
hands the heavy lifting to **Jenkins**:

- **GitLab CI** stages install dependencies, **lint / static-analyse**, and run the **test
  suite** — kept fast, since this is the merge-request gate.
- A final job **triggers Jenkins** via its remote build API (`buildWithParameters`), using
  masked GitLab CI/CD variables (`$JENKINS_URL`, `$JENKINS_TOKEN`) — never inline secrets.
- The **`Jenkinsfile`** is a Declarative pipeline (Checkout → Install → Lint/Test in
  parallel) that pulls secrets from the Jenkins credential store and reports status back to
  the MR.
- A red pipeline **blocks the merge** — CI is the first automated quality gate.

See the `jenkins-expert`, `ci-cd-and-automation`, and `glab` skills for the underlying
GitLab + Jenkins detail.
