## 2026-06-16T06:40:27Z
You are worker_e2e, a worker agent.
Your working directory is d:\Tugas\LLM\autonovel\.agents\worker_e2e/.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Objective:
1. Write the E2E Test Infrastructure documentation file TEST_INFRA.md at the project root (d:\Tugas\LLM\autonovel\TEST_INFRA.md). Use the design catalog and template based on our 4-tier E2E testing strategy:
- Tier 1: Feature Coverage (>=5 cases per feature F1 to F7)
- Tier 2: Boundary & Corner Cases (>=5 cases per feature F1 to F7)
- Tier 3: Cross-Feature Combinations (5 cases)
- Tier 4: Real-World Scenarios (5 cases)
Total tests should be exactly or at least 80 cases.

2. Implement these test cases in:
- d:\Tugas\LLM\autonovel\scratch\test_multi_project.py (containing tests for F2, F4, F5, F7, and related boundaries/scenarios, such as project configuration, atomic registry, CLI project arguments, pipeline lifecycle, and multi-project isolation).
- d:\Tugas\LLM\autonovel\scratch\test_path_contamination.py (containing tests for F1, F3, F6, F7, and related boundaries/scenarios, such as workspace root detection, path helpers directory auto-creation, path containment, git guards, and typesetting sandboxing).

Important:
- Use a subprocess interception mocking strategy (e.g. patching run_pipeline.run_tool and run_pipeline.uv_run with a mock runner that intercepts subprocess execution and simulates writing corresponding files to disk) to mock Anthropic API calls, git actions (if git is missing/unconfigured), and Tectonic typesetting execution. This allows running the tests fast and offline in the CODE_ONLY environment.
- Run the pytest suite using a terminal command to verify that all 80 test cases compile, run, and pass correctly.
- Document the commands run and test results (output and pass/fail counts) in your handoff report (handoff.md) in your working directory.

Scope Boundaries:
- Do not modify production files like utils.py, run_pipeline.py, etc. You are only writing TEST_INFRA.md and test scripts under scratch/.

Provide a detailed handoff message to your caller (id: 802f9463-e9c1-460f-bdbf-b2de0bc722af) once you are done, with the paths to the created files and test run output.
