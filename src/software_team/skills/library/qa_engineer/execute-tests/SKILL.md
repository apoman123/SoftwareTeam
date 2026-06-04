---
name: execute-tests
description: Use after deployment to Staging, to run the full suite as the quality gate that can block a release.
tool: run_tests
---

# Execute the test suite

Run the full suite against the build.

A **red result is a hard gate**: send the work back to engineering with the failure
output rather than promoting it to the next environment.
