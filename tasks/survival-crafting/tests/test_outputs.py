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

def get_all_objects(exclude_main=True):
    out_dir = os.path.join(APP_DIR, "out")
    objs = []
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f.endswith(".o"):
                if exclude_main and (f == "main.o" or "test" in f):
                    continue
                objs.append(os.path.join(root, f))
    return objs

def test_regression_suite():
    """Verify existing tests pass without modification to existing assertions."""
    res_test = subprocess.run(["make", "test"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_test.returncode == 0, f"make test failed:\n{res_test.stdout}\n{res_test.stderr}"

    res_diff = subprocess.run(["git", "diff", "HEAD", "--", "tests/"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_diff.stdout.strip() == "", "Modifications to existing tests/ assertions are prohibited."

def test_synthetic_datapack_crafting(tmp_path):
    """Inject synthetic datapack tags and recipes, then verify shaped offset/mirror, tags, and consumption."""
    os.makedirs(DATAPACK_RECIPE_DIR, exist_ok=True)
    os.makedirs(DATAPACK_TAGS_DIR, exist_ok=True)

    # 1. Inject synthetic item tag
    tag_file = os.path.join(DATAPACK_TAGS_DIR, "adzzat_synth_planks.json")
    tag_data = {
        "values": [
            "minecraft:oak_planks",
            "minecraft:spruce_planks"
        ]
    }
    with open(tag_file, "w", encoding="utf-8") as f:
        json.dump(tag_data, f)

    # 2. Inject synthetic 2x2 shaped recipe using tag
    recipe_shaped_2x2 = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_2x2.json")
    recipe_2x2_data = {
        "type": "minecraft:crafting_shaped",
        "pattern": [
            "# ",
            " #"
        ],
        "key": {
            "#": "#minecraft:adzzat_synth_planks"
        },
        "result": {
            "id": "minecraft:stick",
            "count": 4
        }
    }
    with open(recipe_shaped_2x2, "w", encoding="utf-8") as f:
        json.dump(recipe_2x2_data, f)

    # 3. Inject synthetic horizontally asymmetric shaped recipe
    recipe_asym = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_asym.json")
    recipe_asym_data = {
        "type": "minecraft:crafting_shaped",
        "pattern": [
            "AB"
        ],
        "key": {
            "A": "minecraft:iron_ingot",
            "B": "minecraft:stick"
        },
        "result": {
            "id": "minecraft:lever",
            "count": 1
        }
    }
    with open(recipe_asym, "w", encoding="utf-8") as f:
        json.dump(recipe_asym_data, f)

    # 4. Inject synthetic shapeless recipe
    recipe_shapeless = os.path.join(DATAPACK_RECIPE_DIR, "adzzat_synth_shapeless.json")
    recipe_shapeless_data = {
        "type": "minecraft:crafting_shapeless",
        "ingredients": [
            "minecraft:coal",
            "minecraft:stick"
        ],
        "result": {
            "id": "minecraft:torch",
            "count": 4
        }
    }
    with open(recipe_shapeless, "w", encoding="utf-8") as f:
        json.dump(recipe_shapeless_data, f)

    # 5. Compile and run COBOL verification driver
    driver_cob = """*> Verification driver for survival crafting support
IDENTIFICATION DIVISION.
PROGRAM-ID. VerifyCrafting.

DATA DIVISION.
WORKING-STORAGE SECTION.
    COPY DD-RECIPES.
    COPY DD-TAGS.
    01 DATA-FAILURE             BINARY-CHAR UNSIGNED    VALUE 0.
    01 ROOT-PATH                PIC X(255)              VALUE "data/generated/data/".
    01 PACK-NAME                PIC X(64)               VALUE "minecraft".

    *> Window slots simulation (slot 1 = output, slots 2..10 = 3x3 grid)
    01 WINDOW-INVENTORY-LENGTH  BINARY-LONG UNSIGNED    VALUE 46.
    01 CRAFTING-GRID-SIZE-9     BINARY-LONG UNSIGNED    VALUE 9.
    01 CRAFTING-GRID-SIZE-4     BINARY-LONG UNSIGNED    VALUE 4.
    01 CRAFTING-GRID-START      BINARY-LONG UNSIGNED    VALUE 1.
    01 CRAFTING-OUTPUT-SLOT     BINARY-LONG UNSIGNED    VALUE 0.

    01 TEST-SLOTS.
        02 TEST-SLOT OCCURS 46 TIMES.
            COPY DD-INVENTORY-SLOT REPLACING LEADING ==PREFIX== BY ==TS==.

    *> Registered Item IDs
    01 ID-OAK-PLANKS            BINARY-LONG.
    01 ID-SPRUCE-PLANKS         BINARY-LONG.
    01 ID-STONE                 BINARY-LONG.
    01 ID-IRON-INGOT            BINARY-LONG.
    01 ID-STICK                 BINARY-LONG.
    01 ID-LEVER                 BINARY-LONG.
    01 ID-COAL                  BINARY-LONG.
    01 ID-TORCH                 BINARY-LONG.

    01 SLOT-IDX                 BINARY-LONG UNSIGNED.
    01 STACK-RUN                BINARY-LONG UNSIGNED.

PROCEDURE DIVISION.
    DISPLAY "Init registries and loading datapacks..."
    CALL "Callbacks-Init"
    CALL "Generated-Registries"
    CALL "Generated-Items"

    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:oak_planks" ID-OAK-PLANKS
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:spruce_planks" ID-SPRUCE-PLANKS
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:stone" ID-STONE
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:iron_ingot" ID-IRON-INGOT
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:stick" ID-STICK
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:lever" ID-LEVER
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:coal" ID-COAL
    CALL "Registries-Lookup" USING "minecraft:item" "minecraft:torch" ID-TORCH

    *> Load tags and recipes from datapack
    CALL "Datapack-LoadTags" USING ROOT-PATH PACK-NAME "item" DATA-FAILURE
    CALL "Datapack-LoadRecipes" USING ROOT-PATH PACK-NAME DATA-FAILURE

    *> -------------------------------------------------------------
    *> TEST 1: Shaped 2x2 Offset Matching in 3x3 Grid
    *> Pattern: [P, air], [air, P] where P is from tag
    *> Offsets in 3x3:
    *>   Offset Top-Left:     slot 2, slot 6 (i.e. row 1 col 1, row 2 col 2)
    *>   Offset Top-Right:    slot 3, slot 7 (i.e. row 1 col 2, row 2 col 3)
    *>   Offset Bottom-Left:  slot 5, slot 9 (i.e. row 2 col 1, row 3 col 2)
    *>   Offset Bottom-Right: slot 6, slot 10 (i.e. row 2 col 2, row 3 col 3)
    *> -------------------------------------------------------------
    INITIALIZE TEST-SLOTS
    *> Offset 1: Top-Left
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-SPRUCE-PLANKS TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-STICK
        DISPLAY "FAIL_SHAPED_OFFSET: Top-left failed. Slot count: " TS-SLOT-COUNT(1) " ID: " TS-SLOT-ID(1)
        STOP RUN RETURNING 1
    END-IF

    *> Offset 2: Bottom-Right
    INITIALIZE TEST-SLOTS
    MOVE ID-SPRUCE-PLANKS TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(10)
    MOVE 1 TO TS-SLOT-COUNT(10)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-STICK
        DISPLAY "FAIL_SHAPED_OFFSET: Bottom-right failed."
        STOP RUN RETURNING 2
    END-IF

    *> -------------------------------------------------------------
    *> TEST 2: Horizontal Mirroring vs Vertical Inversion
    *> Asymmetric pattern: [Iron, Stick] -> Lever
    *> Normal: Iron at col 1, Stick at col 2
    *> Mirrored: Stick at col 1, Iron at col 2
    *> Vertical (invalid): Iron at row 1, Stick at row 2 (col 1)
    *> -------------------------------------------------------------
    INITIALIZE TEST-SLOTS
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-LEVER
        DISPLAY "FAIL_MIRROR: Standard orientation failed."
        STOP RUN RETURNING 3
    END-IF

    *> Mirrored horizontal: Stick at col 1, Iron at col 2
    INITIALIZE TEST-SLOTS
    MOVE ID-STICK TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(3)
    MOVE 1 TO TS-SLOT-COUNT(3)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 1 OR TS-SLOT-ID(1) NOT = ID-LEVER
        DISPLAY "FAIL_MIRROR: Horizontally mirrored orientation failed."
        STOP RUN RETURNING 4
    END-IF

    *> Inverted vertical column: Iron at row 1 col 1 (slot 2), Stick at row 2 col 1 (slot 5)
    INITIALIZE TEST-SLOTS
    MOVE ID-IRON-INGOT TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(5)
    MOVE 1 TO TS-SLOT-COUNT(5)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_MIRROR: Vertical rotation incorrectly matched."
        STOP RUN RETURNING 5
    END-IF

    *> -------------------------------------------------------------
    *> TEST 3: Tag Filtering & Rejection
    *> Stone is NOT in adzzat_synth_planks tag -> must reject
    *> -------------------------------------------------------------
    INITIALIZE TEST-SLOTS
    MOVE ID-STONE TO TS-SLOT-ID(2)
    MOVE 1 TO TS-SLOT-COUNT(2)
    MOVE ID-OAK-PLANKS TO TS-SLOT-ID(6)
    MOVE 1 TO TS-SLOT-COUNT(6)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_TAG: Non-member item matched tag ingredient."
        STOP RUN RETURNING 6
    END-IF

    *> -------------------------------------------------------------
    *> TEST 4: Shapeless Recipe
    *> Coal + Stick anywhere in grid -> 4 Torches
    *> -------------------------------------------------------------
    INITIALIZE TEST-SLOTS
    MOVE ID-STICK TO TS-SLOT-ID(4)
    MOVE 1 TO TS-SLOT-COUNT(4)
    MOVE ID-COAL TO TS-SLOT-ID(9)
    MOVE 1 TO TS-SLOT-COUNT(9)

    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-TORCH
        DISPLAY "FAIL_SHAPELESS: Shapeless match failed."
        STOP RUN RETURNING 7
    END-IF

    *> -------------------------------------------------------------
    *> TEST 5: Slot 0 Continuous Consumption Loop
    *> Stack count = 3 of each ingredient -> take slot 0 3 times
    *> -------------------------------------------------------------
    INITIALIZE TEST-SLOTS
    MOVE ID-COAL TO TS-SLOT-ID(2)
    MOVE 3 TO TS-SLOT-COUNT(2)
    MOVE ID-STICK TO TS-SLOT-ID(3)
    MOVE 3 TO TS-SLOT-COUNT(3)

    PERFORM VARYING STACK-RUN FROM 3 BY -1 UNTIL STACK-RUN < 1
        CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
            CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
        IF TS-SLOT-COUNT(1) NOT = 4 OR TS-SLOT-ID(1) NOT = ID-TORCH
            DISPLAY "FAIL_CONSUMPTION: Slot 0 output missing at run " STACK-RUN
            STOP RUN RETURNING 8
        END-IF

        *> Simulate player taking slot 0: decrement input ingredients
        PERFORM VARYING SLOT-IDX FROM 2 BY 1 UNTIL SLOT-IDX > 10
            IF TS-SLOT-COUNT(SLOT-IDX) > 0
                SUBTRACT 1 FROM TS-SLOT-COUNT(SLOT-IDX)
            END-IF
        END-PERFORM
    END-PERFORM

    *> After 3 consumptions, grid must be empty and slot 0 cleared
    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH TEST-SLOTS
        CRAFTING-GRID-SIZE-9 CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
    IF TS-SLOT-COUNT(1) NOT = 0
        DISPLAY "FAIL_CONSUMPTION: Slot 0 not cleared after ingredients exhausted."
        STOP RUN RETURNING 9
    END-IF

    DISPLAY "PASS_CRAFTING"
    STOP RUN RETURNING 0.

END PROGRAM VerifyCrafting.
"""
    driver_path = "/tmp/verify_crafting.cob"
    bin_path = "/tmp/verify_crafting_bin"
    with open(driver_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(driver_cob)

    cobc_cmd = ["cobc", "-x", "-free", "-DGCVERSION=32"] + get_cobc_opts() + [
        "-lstdc++", "-lz", "-o", bin_path, driver_path
    ] + get_all_objects()
    compile_res = subprocess.run(cobc_cmd, cwd=APP_DIR, capture_output=True, text=True)
    assert compile_res.returncode == 0, f"Compilation of crafting test driver failed:\n{compile_res.stderr}"

    run_res = subprocess.run([bin_path], cwd=APP_DIR, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Crafting verification run failed:\n{run_res.stdout}\n{run_res.stderr}"
    assert "PASS_CRAFTING" in run_res.stdout

def test_anti_shortcut():
    """Verify no hardcoded synthetic recipe or tag names in source code."""
    res = subprocess.run(["git", "grep", "-E", "adzzat_synth"], cwd=APP_DIR, capture_output=True, text=True)
    assert res.stdout.strip() == "", f"Anti-shortcut violation: Synthetic IDs found in source tree:\n{res.stdout}"
