# AGENTS

## Repo Overview

- `pick-ltl` is a local Flask app with a vanilla JS frontend.
- The product contract is: one LLM seed formula, then local candidate generation via misconception mutation and syntactic fallback.
- Do not change the architecture to ask the LLM for multiple candidates unless explicitly requested.

## Setup

- Preferred environment: `conda create -n pick-ltl python=3.12`
- Activate with: `conda activate pick-ltl`
- Install Spot with: `conda install -c conda-forge spot`
- Install repo dependencies with: `pip install -e ".[dev]"`

## Common Commands

- Run the app: `./scripts/run.sh`
- Run tests: `pytest -q`

## Important Product Constraints

- Keep misconception codes internal. The UI should show user-friendly explanations, not internal labels.
- If mutation yields exactly one viable candidate, preserve the single-candidate fallback state and the text `We could only get this one.`
- Distinguishing traces are generated locally with Spot. Do not replace that with LLM-generated traces.
- The visible UI currently uses the custom trace renderer in `src/pick_ltl/static/js/app.js`, not Mermaid diagrams.

## Editing Guidance

- Prefer small, local changes that preserve the current API shapes.
- Keep session state browser-owned and exportable/importable as JSON.
- When changing LTL or mutation behavior, add or update tests under `tests/`.
- When changing docs or setup flow, keep `README.md` and `scripts/bootstrap.sh` aligned.
