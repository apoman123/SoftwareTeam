---
name: write-infrastructure-code
description: Describes infrastructure declaratively with Terraform so environments are identical. Use when provisioning environments.
tool: write_source_file
---

# Write infrastructure as code

Describe infrastructure declaratively with **Terraform** so Staging and Production are
provisioned identically from version-controlled code.

- Parameterise per-environment values (image tag, replica count) as **variables**.
- Keep the configuration **idempotent** and reviewable.
