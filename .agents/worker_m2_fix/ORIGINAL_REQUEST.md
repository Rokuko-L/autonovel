## 2026-06-16T06:44:22Z

Implement the required fixes in utils.py, scratch/test_utils.py, and scratch/test_utils_stress.py:
1. In utils.py:
   - In set_project_name(name) and get_project_dir(), add path isolation guards. Specifically, resolve the path of projects root (get_root_dir() / "projects") and the proposed project directory (projects_root / name). Check if proposed_dir is relative to projects_root (using is_relative_to or equivalent checks) and is not equal to projects_root. If not, raise ValueError.
   - In get_novel_title(), check state_path.is_file() and catch OSError along with json.JSONDecodeError and KeyError, to return "the novel" fallback gracefully instead of crashing.
2. In scratch/test_utils.py:
   - Update test_get_novel_title_directory_error to assert that utils.get_novel_title() returns "the novel" fallback rather than raising an exception.
3. In scratch/test_utils_stress.py:
   - Update test_project_name_path_traversal to assert that calling utils.set_project_name("../traversal_test") raises ValueError.

Ensure that all changes are implemented correctly and genuine. Run compile checks and execute the tests to verify:
python -m unittest scratch/test_utils.py
python -m unittest scratch/test_utils_stress.py

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A Forensic Auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.

Write your changes report in d:\Tugas\LLM\autonovel\.agents\worker_m2_fix\changes.md and handoff.md, then send a message back with the path when done.
