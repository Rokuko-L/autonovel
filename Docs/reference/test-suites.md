# Test Suite Index

All suites run **offline** (no API key). `unittest`-based suites can also run
via discovery: `uv run python -m unittest discover -s scratch -p "test_*.py"`.

| Suite | Covers | Runner |
|---|---|---|
| `scratch/test_utils.py` | path helpers, project state (12 tests) | unittest |
| `scratch/test_utils_stress.py` | concurrency + traversal edge cases (6 tests) | unittest |
| `scratch/test_json_repair.py` | damaged-JSON healing layers | script |
| `scratch/test_encoding_healing.py` | UTF-16/latin-1 self-heal | script |
| `scratch/test_multi_project.py` | registry isolation, from-scratch cleanup | script |
| `scratch/test_path_contamination.py` | cross-project leakage, root cleanliness | script |
| `scratch/test_mock_llm.py` | mock harness + validation-retry integration (8 tests) | unittest |

Script-style suites exit non-zero on failure and print `[PASS]/[FAIL]` lines.

## E2E (requires API)

See [test-infra.md](test-infra.md) for the full E2E infrastructure:
project isolation, CLI integration, lifecycle, git-guard containment,
typesetting sandboxing.

## Convention

New offline tests go in `scratch/test_*.py`. A test that needs a real LLM
belongs to the E2E layer, not here.
