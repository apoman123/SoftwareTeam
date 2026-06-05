---
name: execute-tests
description: Runs the full test suite as the quality gate that can block a release. Use after deployment to Staging.
tool: run_tests
---

# Execute the test suite

Run the full suite against the build.

A **red result is a hard gate**: send the work back to engineering with the failure
output rather than promoting it to the next environment.
