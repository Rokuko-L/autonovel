# Project Refactoring Plan

## Objectives
1. Implement isolated project sessions under `projects/`.
2. Define dynamic path resolution helpers in `utils.py` and remove global file/dir variables.
3. Add registry management with atomic updates and project lifecycle (resume/from-scratch) in `run_pipeline.py`.
4. Enforce Option B Git Guards (root `.gitignore` update and project-level sub-repo init).
5. Route all codebase scripts to use dynamic path helpers.
6. Build a comprehensive test suite validating session isolation and path contamination.

## Milestones
- **Milestone 1: E2E Test Suite (Dual Track)**
  - Path: `scratch/test_multi_project.py` and `scratch/test_path_contamination.py`
  - Focus: Establish the E2E verification tests to serve as our acceptance criteria.
- **Milestone 2: Path & Config Refactoring (utils.py)**
  - Focus: Core utility changes, `get_root_dir()`, `get_project_name()`, path helpers, and `save_registry()`.
- **Milestone 3: Pipeline Orchestration & Registry (run_pipeline.py)**
  - Focus: Argparsing (`--project`, `--from-scratch`), metadata registry, state recovery, and Git guards.
- **Milestone 4: Script Routing (Codebase Scripts)**
  - Focus: Update all individual pipeline scripts and typesetting commands to use dynamic path resolution.
- **Milestone 5: Verification & Adversarial Hardening**
  - Focus: Run the test suites, assert zero root contamination, run the Forensic Auditor, and perform the final audit.

## Coordination & Flow
- We will delegate Milestones 1-4 to appropriate subagents (Explorer, Worker, Reviewer).
- We will use a Forensic Auditor to verify integrity and a Challenger to run tests.
