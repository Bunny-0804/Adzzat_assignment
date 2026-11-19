## Statement

Players on the CobolCraft server are experiencing intermittent world-state corruption when interacting with multi-part blocks (such as doors and beds) in `/app`. After toggling or interacting with multi-part blocks repeatedly across different coordinates, subsequent block interactions mutate adjacent blocks at stale coordinates, and block-state property lookups intermittently return corrupted or truncated property strings.

Investigate the block-interaction and block-state handling logic in `/app` and fix the underlying root causes so that multi-part block interactions and state property lookups remain isolated and deterministic across arbitrary sequences of calls.

### Constraints & Acceptance Criteria

- **Root-Cause Fix Only:** Resolve the defects in the core block and state-resolution modules. Do not add coordinate-reset workarounds or block-specific patches in upstream network packet handlers.
- **Generic Behavior:** Do not hardcode specific block identifiers or property string literals to special-case state transitions.
- **Build & Regression Safety:** The project must compile cleanly with zero errors via `make` in `/app`, and all existing tests in the test suite must continue to pass without modification to existing assertions.

## Environment

- **Workspace:** `/app` containing the `CobolCraft` source tree (`src/`, `cpp/`, `tests/`, `Makefile`).
- **Toolchain:** `cobc` (GnuCOBOL 3.x), `g++`, and GNU `make` pre-installed in the container.
- **Build & Test:** Build and run the existing regression suite via `make` in `/app`.
- **Verification:** An external grading harness will compile `/app` and run an automated verification suite testing multi-step interactions on multi-part blocks across varying coordinates and interleaved block-state lookups.

## Difficulty Note

- **Tier:** Medium-Hard (Language-driven)
