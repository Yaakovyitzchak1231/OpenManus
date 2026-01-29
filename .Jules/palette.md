## 2025-03-07 - Repository Formatting
**Learning:** This repository has a `pre-commit` configuration (Black/Isort) but the existing code was not fully compliant. Running `pre-commit run --all-files` results in widespread formatting changes across the codebase.
**Action:** Be prepared for large diffs when running pre-commit checks, or consider checking only modified files if instructed to minimize noise (though the repo instructions explicitly say `run --all-files`).
