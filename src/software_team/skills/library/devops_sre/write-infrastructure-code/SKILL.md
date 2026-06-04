---
name: write-infrastructure-code
description: Use when provisioning environments, to describe infrastructure declaratively with Terraform so environments are identical.
tool: write_source_file
---

# Write infrastructure as code

Describe infrastructure declaratively with **Terraform** so Staging and Production are
provisioned identically from version-controlled code.

- Parameterise per-environment values (image tag, replica count) as **variables**.
- Keep the configuration **idempotent** and reviewable.
