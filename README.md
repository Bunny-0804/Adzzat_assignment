# Azzdat CobolCraft RL Benchmark Suite

An industrial-grade Harbor-format reinforcement learning benchmark suite built on top of [CobolCraft](https://github.com/CobolCraft/CobolCraft) — a high-performance Minecraft 1.21.4 server written in GnuCOBOL 3.x and C++.

This benchmark evaluates autonomous LLM agents on real-world systems programming challenges in COBOL, covering low-level memory calling conventions, static storage semantics, JSON datapack resolution, and stateful grid interactions.

---

## Directory Layout

```text
adzzat-cobolcraft-tasks/
├── tasks/
│   ├── cobol-block-state/             # Task 1: Multi-Block Interaction State Corruption (Language-driven)
│   │   ├── instruction.md             # Verbatim task specification (zero leaked copybooks or internal hints)
│   │   ├── task.toml                  # Harbor task configuration & metadata
│   │   ├── environment/
│   │   │   ├── Dockerfile             # Ubuntu 24.04 container with GnuCOBOL 3.x & toolchains
│   │   │   ├── cobolcraft/            # Clean CobolCraft repo tree (excluding .git)
│   │   │   └── inject_bug.patch       # Verified unified diff injecting interacting defects
│   │   ├── solution/
│   │   │   └── solve.sh               # Executable oracle fix script
│   │   └── tests/
│   │       ├── test.sh                # Executable verifier writing 1 or 0 to /logs/verifier/reward.txt
│   │       └── test_outputs.py        # Pytest verification suite + dynamic COBOL test harness
│   └── survival-crafting/             # Task 2: Implement Survival Crafting Support (Outcome-driven)
│       ├── instruction.md             # Verbatim task specification
│       ├── task.toml                  # Harbor task configuration & metadata
│       ├── environment/
│       │   ├── Dockerfile             # Ubuntu 24.04 container with pre-built assets
│       │   ├── cobolcraft/            # Clean CobolCraft repo tree (excluding .git)
│       │   └── strip_crafting.patch   # Verified unified diff stripping crafting matching & consumption
│       ├── solution/
│       │   └── solve.sh               # Executable oracle fix script
│       └── tests/
│           ├── test.sh                # Executable verifier writing 1 or 0 to /logs/verifier/reward.txt
│           └── test_outputs.py        # Pytest suite with synthetic runtime datapacks
├── web/
│   ├── server.py                      # Zero-dependency Python HTTP server serving tasks from disk
│   └── index.html                     # Two-pane dark/light task catalog showcase
└── README.md                          # Quickstart, architecture, anti-shortcut analysis, & correction log
```

---

## 5-Minute Quickstart

### 1. Running with Harbor CLI

Harbor automates container lifecycle, patch application, agent execution, and reward verification:

```bash
# Verify baseline failure (nop agent):
harbor run -p ./tasks/cobol-block-state -a nop
harbor run -p ./tasks/survival-crafting -a nop

# Verify oracle solution pass (oracle agent):
harbor run -p ./tasks/cobol-block-state -a oracle
harbor run -p ./tasks/survival-crafting -a oracle
```

### 2. Manual Docker Equivalent

You can also build and test tasks manually using plain Docker:

```bash
# Task 1: Build environment and run verifier
cd tasks/cobol-block-state/environment
docker build -t cobol-block-state-env .
docker run --rm -v $(pwd)/../tests:/tests -v /tmp/logs:/logs/verifier cobol-block-state-env /bin/bash /tests/test.sh

# Task 1: Test oracle solution
docker run --rm -v $(pwd)/../solution:/solution -v $(pwd)/../tests:/tests -v /tmp/logs:/logs/verifier \
    cobol-block-state-env /bin/bash -c "/solution/solve.sh && /tests/test.sh && cat /logs/verifier/reward.txt"
```

```bash
# Task 2: Build environment and run verifier
cd tasks/survival-crafting/environment
docker build -t survival-crafting-env .
docker run --rm -v $(pwd)/../tests:/tests -v /tmp/logs:/logs/verifier survival-crafting-env /bin/bash /tests/test.sh

# Task 2: Test oracle solution
docker run --rm -v $(pwd)/../solution:/solution -v $(pwd)/../tests:/tests -v /tmp/logs:/logs/verifier \
    survival-crafting-env /bin/bash -c "/solution/solve.sh && /tests/test.sh && cat /logs/verifier/reward.txt"
```

### 3. Launching the Web Showcase UI

Explore task statements, execution environments, and root-cause systems notes in the built-in catalog UI:

```bash
python3 web/server.py
```

Then open `http://localhost:8000` in your browser. Supports both dark and light modes with zero dependencies.

---

## Architecture & Anti-Shortcut Defense Breakdown

### Task 1: `cobol-block-state` (Medium-Hard / Language-driven)

#### Defect Mechanics
- **Layer A (`src/blocks/door.cob`):** In COBOL, parameters passed in `PROCEDURE DIVISION USING` are passed `BY REFERENCE` by default. When the door interaction handler calculates the coordinate of the other door half, directly applying `ADD 1` / `SUBTRACT 1` to `LK-POSITION-Y` permanently mutates the caller's coordinate variables in upstream network packet handlers (`RecvPacket-UseItemOn`). Subsequent clicks use stale shifted coordinates.
- **Layer B (`src/blocks.cob`):** In `Blocks-Description-GetValue`, using a scratch buffer in `WORKING-STORAGE SECTION` combined with `STRING ... INTO ...` preserves stale trailing bytes across invocations. When transitioning from longer string property values to shorter ones (e.g. `open=false` (5) $\rightarrow$ `open=true` (4)), the buffer contains `"truee"`, breaking downstream conditional checks.

#### Anti-Shortcut Defenses
1. **Dynamic COBOL Test Compilation:** Verification compiles a dedicated test driver linking against `/app`'s compiled object modules (`out/*.o`). It invokes the interact callback across randomized `(X, Y, Z)` coordinate tuples and asserts byte-for-byte caller immutability.
2. **Consecutive String Transition Suite:** Executes consecutive lookups across variable-length properties (`open`, `facing`, `half`) and tests for exact string length and character matches.
3. **AST / Git Diff Guard:** Verifies that fixes were implemented inside `src/blocks/` or `src/blocks.cob`. Rejects modifications to `src/packets/` (upstream packet patching) and rejects hardcoded strings like `"truee"`, `"westh"`, or `"easth"`.

---

### Task 2: `survival-crafting` (Hard / Outcome-driven)

#### Defect Mechanics
The task strips out the crafting output calculation in `src/inventory/inventory.cob` and the callback triggers in `src/inventory/window-crafting.cob` and `src/inventory/window-player.cob`. Agents must implement complete 2x2 and 3x3 crafting matching:
- **2D Sub-Grid Shifting:** Normalizing small patterns (e.g., 2x2 or 1x2) to the origin (top-left) of the 3x3 evaluation grid.
- **Horizontal Mirroring:** Automatically matching horizontally asymmetric recipes in both normal and flipped states while strictly rejecting vertical flips.
- **Datapack `#tag` Resolution:** Accepting any member item defined in `#`-prefixed tags.
- **Continuous Stack Consumption:** Decrementing input ingredients on output pickup and immediately recalculating if the remaining stack produces a craftable item.

#### Anti-Shortcut Defenses
1. **Runtime Synthetic Datapack Injection:** The verification harness generates brand-new synthetic recipe JSON files (`adzzat_synth_2x2`, `adzzat_synth_asym`, `adzzat_synth_shapeless`) and a custom item tag (`#minecraft:adzzat_synth_planks`) at test time. Hardcoded vanilla recipe tables cannot pass.
2. **Grid Offset & Mirror Assertions:** Tests the 2x2 recipe at all 4 corners of the 3x3 grid (top-left, top-right, bottom-left, bottom-right) and verifies horizontal mirroring while asserting vertical flips produce 0 output.
3. **Repeated Extraction Loop:** Places stacks of ingredients (`count = 3`), extracts slot 0 three consecutive times, and asserts proper intermediate recalculation and final exhaustion.
4. **Source Diff Guard:** Scans `/app/src/` to ensure no synthetic identifiers were hardcoded.

---

## AI-Correction Log & Ambiguities Resolved

| Ambiguity / Potential Failure Mode | Root Cause Identified | Engineering Correction Applied |
| :--- | :--- | :--- |
| **Line Endings in Git Patches** | Git diffs generated on Windows default to CRLF, which fail with `git apply` in Linux containers. | Explicitly enforced LF line endings (`\n`) during unified patch generation and verified with `git apply --check`. |
| **COBOL Nested Program Symbols** | Nested programs in COBOL (`Callback-Interact`) cannot always be called directly by external C programs unless registered via pointer. | Leveraged CobolCraft's internal callback registration table (`GetCallback-BlockInteract`) to retrieve the exact function pointer and test interact behavior. |
| **Player Window vs Inventory Slot Reference** | `window-player.cob` previously used `PLAYER-WINDOW-SLOTS` in `UpdateCrafting`, which points to container memory instead of player inventory. | Corrected the oracle fix to pass `PLAYER-INVENTORY(LK-PLAYER)` to ensure 2x2 player inventory crafting updates deterministically. |
| **Information Leakage in Instructions** | Tasks must test reasoning from problem statements, not leaked implementation details. | Strictly sanitized `instruction.md` files: no copybook names (`DD-*`), no section hints (`WORKING-STORAGE`), and no source file paths inside `src/`. |
| **Zero External Web Dependencies** | Benchmark web dashboards relying on external CDN scripts fail in airgapped container environments. | Built `web/server.py` with standard library Python and wrote zero-dependency vanilla CSS/JS for `web/index.html`. |
