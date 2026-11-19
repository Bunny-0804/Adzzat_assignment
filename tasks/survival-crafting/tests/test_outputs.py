import os
import json
import subprocess
import pytest

APP_DIR = "/app"
DATAPACK_RECIPE_DIR = os.path.join(APP_DIR, "data", "generated", "data", "minecraft", "recipe")
DATAPACK_TAGS_DIR = os.path.join(APP_DIR, "data", "generated", "data", "minecraft", "tags", "item")

def get_cobc_opts():
    cpy_dir = os.path.join(APP_DIR, "src", "_copybooks")
    subdirs = [os.path.join(cpy_dir, d) for d in os.listdir(cpy_dir) if os.path.isdir(os.path.join(cpy_dir, d))]
    include_flags = ["-I", cpy_dir]
    for d in subdirs:
        include_flags.extend(["-I", d])
    test_cpy = os.path.join(APP_DIR, "tests", "_copybooks")
    if os.path.exists(test_cpy):
        include_flags.extend(["-I", test_cpy])
    return include_flags

def get_all_objects():
    out_dir = os.path.join(APP_DIR, "out")
    objs = []
    for root, _, files in os.walk(out_dir):
        if "tests" in root:
            continue
        for f in files:
            if f.endswith(".o") and f != "main.o":
                objs.append(os.path.join(root, f))
    return objs

def test_regression_suite():
    """Verify existing tests pass and pre-existing tests/ assertions remain unmodified."""
    res_test = subprocess.run(["make", "test"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_test.returncode == 0, f"make test failed:\n{res_test.stdout}\n{res_test.stderr}"

    res_diff = subprocess.run(["git", "diff", "HEAD", "--", "tests/"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_diff.stdout.strip() == "", "Modifications to existing tests/ assertions are prohibited."

def test_synthetic_datapack_and_window_crafting():
    """Inject synthetic recipes, tags, and unsupported recipe types; verify 2x2/3x3 crafting and consumption."""
    os.makedirs(DATAPACK_RECIPE_DIR, exist_ok=True)
    os.makedirs(DATAPACK_TAGS_DIR, exist_ok=True)

    created_files = []

    try:
        # 1. Custom item tag #minecraft:adzzat_synthetic_tag with two distinct valid items
        tag_file = os.path.join(DATAPACK_TAGS_DIR, "adzzat_synthetic_tag.json")
        with open(tag_file, "w", encoding="utf-8") as f:
            json.dump({
                "values": [
                    "minecraft:oak_planks",
                    "minecraft:birch_planks"
                ]
            }, f)
        created_files.append(tag_file)

        # 2. Synthetic 2x2 shaped recipe: #minecraft:adzzat_synthetic_tag + concrete stick
        recipe_2x2_file = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_2x2.json")
        with open(recipe_2x2_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "minecraft:crafting_shaped",
                "pattern": [
                    "# ",
                    " S"
                ],
                "key": {
                    "#": "#minecraft:adzzat_synthetic_tag",
                    "S": "minecraft:stick"
                },
                "result": {
                    "id": "minecraft:torch",
                    "count": 4
                }
            }, f)
        created_files.append(recipe_2x2_file)

        # 3. Asymmetric L-shaped recipe (tests horizontal mirror match vs vertical-only flip reject)
        # Pattern:
        # "I "
        # "IS"  (L-shape)
        recipe_asym_file = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_asym_l.json")
        with open(recipe_asym_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "minecraft:crafting_shaped",
                "pattern": [
                    "I ",
                    "IS"
                ],
                "key": {
                    "I": "minecraft:iron_ingot",
                    "S": "minecraft:stick"
                },
                "result": {
                    "id": "minecraft:lever",
                    "count": 1
                }
            }, f)
        created_files.append(recipe_asym_file)

        # 4. 1x3 vertical recipe (matches col 1, 2, 3 in 3x3; must NOT fit in 2x2 grid)
        recipe_1x3_file = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_1x3_vertical.json")
        with open(recipe_1x3_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "minecraft:crafting_shaped",
                "pattern": [
                    "G",
                    "G",
                    "G"
                ],
                "key": {
                    "G": "minecraft:gold_ingot"
                },
                "result": {
                    "id": "minecraft:clock",
                    "count": 1
                }
            }, f)
        created_files.append(recipe_1x3_file)

        # 5. Shapeless recipe with two overlapping tag ingredients (multiset test)
        recipe_shapeless_file = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_shapeless_multiset.json")
        with open(recipe_shapeless_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "minecraft:crafting_shapeless",
                "ingredients": [
                    "#minecraft:adzzat_synthetic_tag",
                    "#minecraft:adzzat_synthetic_tag"
                ],
                "result": {
                    "id": "minecraft:bowl",
                    "count": 2
                }
            }, f)
        created_files.append(recipe_shapeless_file)

        # 6. Unsupported recipe type (smelting) to test clean ingestion without crashing
        recipe_unsupported_file = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_unsupported_smelting.json")
        with open(recipe_unsupported_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "minecraft:smelting",
                "ingredient": "minecraft:raw_iron",
                "result": {
                    "id": "minecraft:iron_ingot"
                },
                "experience": 0.7,
                "cookingtime": 200
            }, f)
        created_files.append(recipe_unsupported_file)

        # Compile and execute the full COBOL verification harness
        driver_cob = """*> Verification driver for survival crafting and datapack ingestion
IDENTIFICATION DIVISION.
PROGRAM-ID. VerifyCraftingSuite.

DATA DIVISION.
WORKING-STORAGE SECTION.
    COPY DD-RECIPES.
    COPY DD-TAGS.
    COPY DD-PLAYERS.
    01 DATA-FAILURE             BINARY-CHAR UNSIGNED    VALUE 0.
    01 ROOT-PATH                PIC X(255)              VALUE "data/generated/data/".
    01 PACK-NAME                PIC X(64)               VALUE "minecraft".

    01 WINDOW-INVENTORY-LENGTH  BINARY-LONG UNSIGNED    VALUE 46.
    01 PLAYER-INVENTORY-LENGTH  BINARY-LONG UNSIGNED    VALUE 46.
    01 CRAFTING-GRID-SIZE-9     BINARY-LONG UNSIGNED    VALUE 9.
    01 CRAFTING-GRID-SIZE-4     BINARY-LONG UNSIGNED    VALUE 4.
    01 CRAFTING-GRID-START      BINARY-LONG UNSIGNED    VALUE 1.
    01 CRAFTING-OUTPUT-SLOT     BINARY-LONG UNSIGNED    VALUE 0.

    01 TEST-SLOTS.
        02 TEST-SLOT OCCURS 46 TIMES.
            COPY DD-INVENTORY-SLOT REPLACING LEADING ==PREFIX== BY ==TS==.

    *> Registered Item IDs
    01 ID-OAK-PLANKS            BINARY-LONG.
    01 ID-BIRCH-PLANKS          BINARY-LONG.
    01 ID-STONE                 BINARY-LONG.
    01 ID-STICK                 BINARY-LONG.
    01 ID-TORCH                 BINARY-LONG.
    01 ID-IRON-INGOT            BINARY-LONG.
    01 ID-LEVER                 BINARY-LONG.
    01 ID-GOLD-INGOT            BINARY-LONG.
    01 ID-CLOCK                 BINARY-LONG.
    01 ID-BOWL                  BINARY-LONG.

    01 SLOT-IDX                 BINARY-LONG UNSIGNED.
    01 STACK-RUN                BINARY-LONG UNSIGNED.
    01 LK-SYNC-REQ              BINARY-CHAR UNSIGNED.
    01 PLAYER-ID                BINARY-LONG             VALUE 1.
    01 EMPTY-CURSOR-SLOT.
        COPY DD-INVENTORY-SLOT REPLACING LEADING ==PREFIX== BY ==EMPTY-CURSOR==.

PROCEDURE DIVISION.
    DISPLAY "Initializing registries and loading datapacks..."
    CALL "Callbacks-Init"
    CALL "Generated-Registries"
    CALL "Generated-Items"

    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:oak_planks" ID-OAK-PLANKS
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:birch_planks" ID-BIRCH-PLANKS
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:stone" ID-STONE
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:stick" ID-STICK
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:torch" ID-TORCH
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:iron_ingot" ID-IRON-INGOT
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:lever" ID-LEVER
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:gold_ingot" ID-GOLD-INGOT
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:clock" ID-CLOCK
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:bowl" ID-BOWL

    *> Datapack ingestion: must load custom tags & recipes and skip unsupported recipes
    CALL "Datapack-LoadTags" USING ROOT-PATH PACK-NAME "item" DATA-FAILURE
    IF DATA-FAILURE NOT = 0
        DISPLAY "FAIL: Datapack-LoadTags returned failure"
        STOP RUN RETURNING 1
    END-IF

    CALL "Datapack-LoadRecipes" USING ROOT-PATH PACK-NAME DATA-FAILURE
    IF DATA-FAILURE NOT = 0
        DISPLAY "FAIL: Datapack-LoadRecipes failed on unsupported/custom recipes"
        STOP RUN RETURNING 2
    END-IF

    *> Register window callbacks
    CALL "RegisterWindow-Crafting"
    CALL "RegisterWindow-Player"

    *> =============================================================
    *> TEST 1: Shaped 2x2 Offset Matching in 3x3 Grid
    *> Pattern: [# ,  S] where # is from #minecraft:adzzat_synthetic_tag
    *> =============================================================
    INITIALIZE TEST-SLOTS
    *> 1A: Top-Left offset (slot 1, slot 5 in 3x3 grid / indices 2, 6)
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-TORCH
        DISPLAY "FAIL_1A: 2x2 shaped top-left offset failed"
        STOP RUN RETURNING 10
    END-IF

    *> 1B: Bottom-Right offset (slot 5, slot 9 in 3x3 grid / indices 6, 10)
    INITIALIZE TEST-SLOTS
    MOVE ID-BIRCH-PLANKS TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)
    MOVE ID-STICK TO TS-SLOT-ID(10)
    MOVE 1 TO TS-SLOT-COUNT(10)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-TORCH
        DISPLAY "FAIL_1B: 2x2 shaped bottom-right offset with tag member 2 failed"
        STOP RUN RETURNING 11
    END-IF

    *> 1C: Tag member rejection (stone is not in tag)
    INITIALIZE TEST-SLOTS
    MOVE ID-STONE TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_1C: Non-member item matched tag recipe"
        STOP RUN RETURNING 12
    END-IF

    *> =============================================================
    *> TEST 2: Asymmetric L-Shape Horizontal Mirroring vs Vertical Flip
    *> Pattern: ["I ", "IS"] -> Lever
    *> =============================================================
    INITIALIZE TEST-SLOTS
    *> 2A: Standard orientation: col 1=[I, I], col 2=[air, S] (indices 2, 5, 6)
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(5)
    MOVE 1 TO TS-SLOT-COUNT(5)
    MOVE ID-STICK TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-LEVER
        DISPLAY "FAIL_2A: Standard L-shape failed"
        STOP RUN RETURNING 20
    END-IF

    *> 2B: Horizontal mirror: col 1=[air, S], col 2=[I, I] (indices 3, 5, 6)
    INITIALIZE TEST-SLOTS
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)
    MOVE ID-STICK TO TS-SLOT-ID(5)
    MOVE 1 TO TS-SLOT-COUNT(5)
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-LEVER
        DISPLAY "FAIL_2B: Horizontally mirrored L-shape failed"
        STOP RUN RETURNING 21
    END-IF

    *> 2C: Vertical-only flip: ["IS", "I "] (indices 2, 3, 5) -> must be rejected!
    INITIALIZE TEST-SLOTS
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(5)
    MOVE 1 TO TS-SLOT-COUNT(5)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_2C: Vertical flip incorrectly accepted"
        STOP RUN RETURNING 22
    END-IF

    *> =============================================================
    *> TEST 3: 1x3 Vertical Recipe in 3x3 Grid vs 2x2 Player Grid
    *> =============================================================
    *> 3A: Column 1 of 3x3 (indices 2, 5, 8)
    INITIALIZE TEST-SLOTS
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(5)
    MOVE 1 TO TS-SLOT-COUNT(5)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(8)
    MOVE 1 TO TS-SLOT-COUNT(8)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-CLOCK
        DISPLAY "FAIL_3A: 1x3 vertical recipe in column 1 failed"
        STOP RUN RETURNING 30
    END-IF

    *> 3B: Column 3 of 3x3 (indices 4, 7, 10)
    INITIALIZE TEST-SLOTS
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(4)
    MOVE 1 TO TS-SLOT-COUNT(4)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(7)
    MOVE 1 TO TS-SLOT-COUNT(7)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(10)
    MOVE 1 TO TS-SLOT-COUNT(10)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-CLOCK
        DISPLAY "FAIL_3B: 1x3 vertical recipe in column 3 failed"
        STOP RUN RETURNING 31
    END-IF

    *> 3C: 1x3 in 2x2 player inventory grid (slots 1..4): height 3 does not fit -> output must be 0!
    INITIALIZE TEST-SLOTS
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)
    MOVE ID-GOLD-INGOT TO TS-SLOT-ID(4)
    MOVE 1 TO TS-SLOT-COUNT(4)

    CALL "Inventory-UpdateCraftingOutput" USING PLAYER-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-4 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_3C: 1x3 vertical recipe illegally matched 2x2 grid"
        STOP RUN RETURNING 32
    END-IF

    *> =============================================================
    *> TEST 4: Shapeless Recipe with Overlapping Tag Ingredients (Multiset)
    *> Recipe needs 2 items from #minecraft:adzzat_synthetic_tag
    *> =============================================================
    INITIALIZE TEST-SLOTS
    *> 4A: Only 1 tagged item in grid -> must reject!
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_4A: Single tagged item satisfied 2-ingredient recipe"
        STOP RUN RETURNING 40
    END-IF

    *> 4B: Two distinct tagged items in grid (oak + birch) -> matches!
    MOVE ID-BIRCH-PLANKS TO TS-SLOT-ID(8)
    MOVE 1 TO TS-SLOT-COUNT(8)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 2 OR TS-SLOT-ID(1) NOT = ID-BOWL
        DISPLAY "FAIL_4B: Two tagged items failed to produce shapeless output"
        STOP RUN RETURNING 41
    END-IF

    *> =============================================================
    *> TEST 5: Slot 0 Extraction & Continuous Stack Consumption
    *> Window set-slot callback execution with empty cursor
    *> =============================================================
    INITIALIZE TEST-SLOTS
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(2)
    MOVE 3 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(6)
    MOVE 3 TO TS-SLOT-COUNT(6)

    *> Initialize player window state
    MOVE 0 TO PLAYER-MOUSE-SLOT-COUNT(PLAYER-ID)
    PERFORM VARYING SLOT-IDX FROM 1 BY 1 UNTIL SLOT-IDX > 46
        MOVE TS-SLOT(SLOT-IDX) TO PLAYER-WINDOW-SLOT(PLAYER-ID, SLOT-IDX)
    END-PERFORM

    *> Initial calculation
    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH PLAYER-WINDOW-SLOTS(PLAYER-ID)
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF PLAYER-WINDOW-SLOT-COUNT(PLAYER-ID, 1) NOT = 4
        DISPLAY "FAIL_5A: Initial output calculation failed"
        STOP RUN RETURNING 50
    END-IF

    *> Simulate player taking slot 0 with empty cursor (3 consecutive runs)
    PERFORM VARYING STACK-RUN FROM 3 BY -1 UNTIL STACK-RUN < 1
        IF PLAYER-WINDOW-SLOT-COUNT(PLAYER-ID, 1) NOT = 4 OR PLAYER-WINDOW-SLOT-ID(PLAYER-ID, 1) NOT = ID-TORCH
            DISPLAY "FAIL_5B: Slot 0 output not present at iteration " STACK-RUN
            STOP RUN RETURNING 51
        END-IF

        *> Take slot 0 via Callback-SetSlot with empty slot
        INITIALIZE EMPTY-CURSOR-SLOT
        CALL "Callback-SetSlot" USING PLAYER-ID 0 EMPTY-CURSOR-SLOT LK-SYNC-REQ
    END-PERFORM

    *> After 3 extractions, inputs must be completely exhausted (count = 0) and slot 0 empty
    IF PLAYER-WINDOW-SLOT-COUNT(PLAYER-ID, 2) NOT = 0 OR PLAYER-WINDOW-SLOT-COUNT(PLAYER-ID, 6) NOT = 0
        DISPLAY "FAIL_5C: Input slots not cleared after exhaustion"
        STOP RUN RETURNING 52
    END-IF

    IF PLAYER-WINDOW-SLOT-COUNT(PLAYER-ID, 1) NOT = 0
        DISPLAY "FAIL_5D: Slot 0 not cleared after ingredients exhausted"
        STOP RUN RETURNING 53
    END-IF

    DISPLAY "PASS_FULL_CRAFTING_SUITE"
    STOP RUN RETURNING 0.

END PROGRAM VerifyCraftingSuite.
"""
        harness_path = "/tmp/verify_crafting_suite.cob"
        bin_path = "/tmp/verify_crafting_suite_bin"
        with open(harness_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(driver_cob)

        cobc_cmd = ["cobc", "-x", "-free", "-DGCVERSION=32"] + get_cobc_opts() + [
            "-lstdc++", "-lz", "-o", bin_path, harness_path
        ] + get_all_objects()
        compile_res = subprocess.run(cobc_cmd, cwd=APP_DIR, capture_output=True, text=True)
        assert compile_res.returncode == 0, f"Compilation of crafting test suite driver failed:\n{compile_res.stderr}"

        run_res = subprocess.run([bin_path], cwd=APP_DIR, capture_output=True, text=True)
        assert run_res.returncode == 0, f"Crafting verification run failed:\n{run_res.stdout}\n{run_res.stderr}"
        assert "PASS_FULL_CRAFTING_SUITE" in run_res.stdout

    finally:
        # Guarantee cleanup of all synthetic datapack and tag files
        for f in created_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

def test_structural_git_diff_check():
    """Verify changes are contained to inventory modules without modifying pre-existing tests/."""
    res = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=APP_DIR, capture_output=True, text=True)
    assert res.returncode == 0, f"git diff failed:\n{res.stderr}"
    modified_files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]

    # No modifications to pre-existing tests/
    test_mods = [f for f in modified_files if f.startswith("tests/")]
    assert len(test_mods) == 0, f"Anti-shortcut violation: pre-existing test files were modified: {test_mods}"

    # Inventory modules must be modified
    inv_mods = [f for f in modified_files if f.startswith("src/inventory/")]
    assert len(inv_mods) > 0, f"Anti-shortcut violation: No inventory modules were modified. Modified: {modified_files}"
