# Context for Autonovel Pipeline Refactoring

## Active Codebase Context
- **Base Directory**: `d:\Tugas\LLM\autonovel`
- **Key Modules**:
  - `utils.py`: Contains API call logic, helper functions, and needs path helpers/registry management.
  - `run_pipeline.py`: Main entry point. Needs command-line arguments, project registry updates, state recovery, and Git guards.
  - Script Files (to be routed):
    - `evaluate.py`
    - `adversarial_edit.py`
    - `apply_cuts.py`
    - `build_outline.py`
    - `build_arc_summary.py`
    - `gen_brief.py`
    - `reader_panel.py`
    - `review.py`
    - `typeset/build_tex.py`
    - other generator/script files as needed.

## Key Requirements
- **Registry**: Located at `projects/registry.json`. Save atomically.
- **Git Guards**:
  - Append `projects/` to root `.gitignore`.
  - Initialize isolated `.git` in new projects if `.git` is missing.
- **Path Resolution**: Must derive roots and paths dynamically, preventing any creation in the root directory.
- **Typesetting**: Tectonic/LaTeX runs with cwd set to project typeset dir.
