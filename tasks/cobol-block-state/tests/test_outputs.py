import os
import subprocess
import pytest

APP_DIR = "/app"

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
        # Exclude tests/ directory objects and any standalone binaries
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

    # Verify no test assertion tampering in /app/tests/
    res_diff = subprocess.run(["git", "diff", "HEAD", "--", "tests/"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_diff.stdout.strip() == "", "Modifications to existing tests/ assertions are prohibited."

def test_interleaved_end_to_end_driver():
    """Execute interleaved verification driver testing coordinate immutability and shrinking property isolation."""
    driver_cob = """*> Interleaved Verification Driver
IDENTIFICATION DIVISION.
PROGRAM-ID. VerifyInterleavedDriver.

DATA DIVISION.
WORKING-STORAGE SECTION.
    COPY DD-CALLBACKS.
    01 LK-PLAYER                BINARY-LONG             VALUE 1.
    01 LK-ITEM-NAME             PIC X(64)               VALUE "minecraft:air".
    01 LK-POSITION.
        02 LK-POSITION-X        BINARY-LONG.
        02 LK-POSITION-Y        BINARY-LONG.
        02 LK-POSITION-Z        BINARY-LONG.
    01 LK-FACE                  BINARY-LONG             VALUE 0.
    01 LK-CURSOR.
        02 LK-CURSOR-X          FLOAT-SHORT             VALUE 0.0.
        02 LK-CURSOR-Y          FLOAT-SHORT             VALUE 0.0.
        02 LK-CURSOR-Z          FLOAT-SHORT             VALUE 0.0.

    01 SAVED-X                  BINARY-LONG.
    01 SAVED-Y                  BINARY-LONG.
    01 SAVED-Z                  BINARY-LONG.

    01 FILE-BLOCKS              PIC X(255)              VALUE "data/generated/reports/blocks.json".
    01 DATA-BUFFER              PIC X(10000000).
    01 DATA-BUFFER-LEN          BINARY-LONG UNSIGNED.
    01 DATA-FAILURE             BINARY-CHAR UNSIGNED.

    01 INTERACT-PTR             PROGRAM-POINTER.
    01 DOOR-BLOCK-ID            BINARY-LONG.
    01 DOOR-MIN-STATE           BINARY-LONG.
    01 DOOR-MAX-STATE           BINARY-LONG.

    COPY DD-BLOCK-STATE REPLACING LEADING ==PREFIX== BY ==TEST-STATE==.
    01 RETRIEVED-VALUE          PIC X(64).

PROCEDURE DIVISION.
    CALL "Callbacks-Init"
    CALL "Generated-Registries"
    CALL "Files-ReadAll" USING FILE-BLOCKS DATA-BUFFER DATA-BUFFER-LEN DATA-FAILURE
    IF DATA-FAILURE NOT = 0
        DISPLAY "ERR: Files-ReadAll failed on blocks.json"
        STOP RUN RETURNING 3
    END-IF
    CALL "Blocks-Parse" USING DATA-BUFFER DATA-BUFFER-LEN DATA-FAILURE
    IF DATA-FAILURE NOT = 0
        DISPLAY "ERR: Blocks-Parse failed"
        STOP RUN RETURNING 4
    END-IF

    CALL "RegisterBlock-Door"

    CALL "Registries-Lookup" USING "minecraft:block" "minecraft:oak_door" DOOR-BLOCK-ID
    CALL "Blocks-GetStateIds" USING DOOR-BLOCK-ID DOOR-MIN-STATE DOOR-MAX-STATE
    CALL "GetCallback-BlockInteract" USING DOOR-MIN-STATE INTERACT-PTR

    IF INTERACT-PTR = NULL
        SET INTERACT-PTR TO ENTRY "Callback-Interact"
    END-IF

    IF INTERACT-PTR = NULL
        DISPLAY "ERR: INTERACT-PTR NULL"
        STOP RUN RETURNING 2
    END-IF

    *> === PHASE 1: Lower Door Half Interaction at (X1, Y1, Z1) ===
    MOVE 147 TO LK-POSITION-X
    MOVE 64 TO LK-POSITION-Y
    MOVE -89 TO LK-POSITION-Z

    MOVE LK-POSITION-X TO SAVED-X
    MOVE LK-POSITION-Y TO SAVED-Y
    MOVE LK-POSITION-Z TO SAVED-Z

    CALL INTERACT-PTR USING LK-PLAYER LK-ITEM-NAME LK-POSITION LK-FACE LK-CURSOR

    IF LK-POSITION-X NOT = SAVED-X OR LK-POSITION-Y NOT = SAVED-Y OR LK-POSITION-Z NOT = SAVED-Z
        DISPLAY "FAIL_PHASE1: Y mutated from " SAVED-Y " to " LK-POSITION-Y
        STOP RUN RETURNING 1
    END-IF

    *> === PHASE 2: Interleaved Multi-Property Shrinking Transitions ===
    *> 2A: Door 'open' property: 'false' (5) -> 'true' (4)
    MOVE "minecraft:oak_door" TO TEST-STATE-NAME
    MOVE 3 TO TEST-STATE-PROPERTY-COUNT

    MOVE "open" TO TEST-STATE-PROPERTY-NAME(1)
    MOVE "false" TO TEST-STATE-PROPERTY-VALUE(1)

    MOVE "half" TO TEST-STATE-PROPERTY-NAME(2)
    MOVE "lower" TO TEST-STATE-PROPERTY-VALUE(2)

    MOVE "facing" TO TEST-STATE-PROPERTY-NAME(3)
    MOVE "south" TO TEST-STATE-PROPERTY-VALUE(3)

    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "open" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "false"
        DISPLAY "FAIL_2A_INIT: expected 'false', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 10
    END-IF

    MOVE "true" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "open" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "true"
        DISPLAY "FAIL_2A_SHRINK: expected 'true', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 11
    END-IF

    *> 2B: Door 'facing' property: 'south' (5) -> 'east' (4)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "south"
        DISPLAY "FAIL_2B_INIT: expected 'south', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 12
    END-IF

    MOVE "east" TO TEST-STATE-PROPERTY-VALUE(3)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "east"
        DISPLAY "FAIL_2B_SHRINK: expected 'east', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 13
    END-IF

    *> 2C: Non-door block property: Note Block 'instrument': 'xylophone' (9) -> 'flute' (5)
    MOVE "minecraft:note_block" TO TEST-STATE-NAME
    MOVE 1 TO TEST-STATE-PROPERTY-COUNT
    MOVE "instrument" TO TEST-STATE-PROPERTY-NAME(1)
    MOVE "xylophone" TO TEST-STATE-PROPERTY-VALUE(1)

    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "instrument" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "xylophone"
        DISPLAY "FAIL_2C_INIT: expected 'xylophone', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 14
    END-IF

    MOVE "flute" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "instrument" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "flute"
        DISPLAY "FAIL_2C_SHRINK: expected 'flute', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 15
    END-IF

    *> === PHASE 3: Upper Door Half Interaction at (X2, Y2, Z2) ===
    MOVE -512 TO LK-POSITION-X
    MOVE 71 TO LK-POSITION-Y
    MOVE 1024 TO LK-POSITION-Z

    MOVE LK-POSITION-X TO SAVED-X
    MOVE LK-POSITION-Y TO SAVED-Y
    MOVE LK-POSITION-Z TO SAVED-Z

    CALL INTERACT-PTR USING LK-PLAYER LK-ITEM-NAME LK-POSITION LK-FACE LK-CURSOR

    IF LK-POSITION-X NOT = SAVED-X OR LK-POSITION-Y NOT = SAVED-Y OR LK-POSITION-Z NOT = SAVED-Z
        DISPLAY "FAIL_PHASE3: Upper half Y mutated from " SAVED-Y " to " LK-POSITION-Y
        STOP RUN RETURNING 20
    END-IF

    *> Verify lookups remain isolated after upper half interaction
    MOVE "minecraft:oak_door" TO TEST-STATE-NAME
    MOVE 1 TO TEST-STATE-PROPERTY-COUNT
    MOVE "facing" TO TEST-STATE-PROPERTY-NAME(1)
    MOVE "north" TO TEST-STATE-PROPERTY-VALUE(1)

    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE

    MOVE "west" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "west"
        DISPLAY "FAIL_POST_PHASE3: expected 'west', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 21
    END-IF

    DISPLAY "PASS_INTERLEAVED_HARNESS"
    STOP RUN RETURNING 0.

END PROGRAM VerifyInterleavedDriver.
"""
    harness_path = "/tmp/verify_interleaved.cob"
    bin_path = "/tmp/verify_interleaved_bin"
    try:
        with open(harness_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(driver_cob)

        cobc_cmd = ["cobc", "-x", "-free", "-DGCVERSION=32"] + get_cobc_opts() + [
            "-lstdc++", "-lz", "-o", bin_path, harness_path
        ] + get_all_objects()
        compile_res = subprocess.run(cobc_cmd, cwd=APP_DIR, capture_output=True, text=True)
        assert compile_res.returncode == 0, f"Compilation of interleaved verification driver failed:\n{compile_res.stderr}"

        run_res = subprocess.run([bin_path], cwd=APP_DIR, capture_output=True, text=True)
        assert run_res.returncode == 0, f"Interleaved verification check failed:\n{run_res.stdout}\n{run_res.stderr}"
        assert "PASS_INTERLEAVED_HARNESS" in run_res.stdout
    finally:
        for p in [harness_path, bin_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

def test_structural_git_diff_check():
    """Ensure fixes were applied to core block state modules without touching upstream packet handlers."""
    res = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=APP_DIR, capture_output=True, text=True)
    assert res.returncode == 0, f"git diff failed:\n{res.stderr}"
    modified_files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]

    # 1. No modifications to pre-existing tests/
    test_mods = [f for f in modified_files if f.startswith("tests/")]
    assert len(test_mods) == 0, f"Anti-shortcut violation: pre-existing test files were modified: {test_mods}"

    # 2. At least one file under src/blocks/ or src/blocks.cob must be modified
    core_block_mods = [f for f in modified_files if f.startswith("src/blocks/") or f == "src/blocks.cob"]
    assert len(core_block_mods) > 0, (
        f"Anti-shortcut violation: No core block or state modules were modified. "
        f"Expected modifications under src/blocks/ or src/blocks.cob. Modified: {modified_files}"
    )

    # 3. Reject solutions that only modify src/packets/
    packet_mods = [f for f in modified_files if f.startswith("src/packets/")]
    if len(packet_mods) > 0:
        assert len(core_block_mods) > 0, "Anti-shortcut violation: Packet handler workaround detected."
