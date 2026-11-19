## Statement

The CobolCraft server in `/app` currently loads vanilla datapack definitions on startup and allows players to open both the 2x2 player inventory crafting grid and the 3x3 crafting table interface and move items between slots. However, placing valid ingredient combinations into either crafting grid never produces a craftable result item or consumes input ingredients.

Implement end-to-end survival crafting support in `/app` so players can craft items normally through both crafting interfaces.

### Observable Requirements & Constraints

- **Datapack-Driven Recipes:** Recipes must be loaded dynamically from the server's datapack JSON files at startup rather than hardcoded in source code. Unsupported recipe types present in the datapack directory must be skipped cleanly without aborting server startup.
- **Crafting Grid & Recipe Semantics:**
  - Support both shaped (`minecraft:crafting_shaped`) and shapeless (`minecraft:crafting_shapeless`) recipes in both the 2x2 player inventory crafting grid and the 3x3 crafting table grid.
  - Shaped recipes smaller than the active grid must match regardless of offset position within the grid and must also match when mirrored horizontally.
  - Support both concrete item IDs and `#`-prefixed item tags defined by the loaded datapack tags.
- **Slot Interaction & Consumption:**
  - Whenever input slots change and match a valid recipe, the crafting output slot (`0`) must reflect the resulting item and stack count; if no recipe matches, slot `0` must be cleared.
  - Taking the crafted output from slot `0` must decrement each consumed input slot by `1` (clearing slots that reach `0`) and immediately recalculate whether the remaining grid items still form a valid recipe.

## Environment

- **Workspace:** `/app` containing the `CobolCraft` repository (`src/`, `cpp/`, `tests/`, `Makefile`, and runtime datapack/registry assets).
- **Toolchain:** `cobc` (GnuCOBOL 3.x), `g++`, and GNU `make` pre-installed in the container.
- **Verification:** An external grading harness will build `/app`, load the datapack recipes and tags, and exercise both 2x2 and 3x3 crafting workflows (shaped offset matching, horizontal mirroring, tag-based ingredients, shapeless matching, output extraction, and ingredient decrementing) alongside the existing regression suite.

## Difficulty Note

- **Tier:** Hard (Outcome-driven)
