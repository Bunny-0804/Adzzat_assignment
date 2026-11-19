import os
import subprocess
import random
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
    """Verify existing tests pass and test suite assertions are unmodified."""
    res_test = subprocess.run(["make", "test"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_test.returncode == 0, f"make test failed:\n{res_test.stdout}\n{res_test.stderr}"

    # Verify no test assertion tampering in /app/tests/
    res_diff = subprocess.run(["git", "diff", "HEAD", "--", "tests/"], cwd=APP_DIR, capture_output=True, text=True)
    assert res_diff.stdout.strip() == "", "Modifications to existing tests/ assertions are prohibited."

def test_caller_coordinate_immutability():
    """Verify caller coordinates in LINKAGE SECTION remain immutable across callback calls."""
    harness_src = """*> Test harness for coordinate immutability
IDENTIFICATION DIVISION.
PROGRAM-ID. VerifyCoordImmutability.

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

    01 INTERACT-PTR             PROGRAM-POINTER.
    01 TEST-RESULT              BINARY-LONG             VALUE 0.
    01 STATE-ID                 BINARY-LONG             VALUE 1.

PROCEDURE DIVISION.
    CALL "Callbacks-Init"

    *> Set a dummy door callback entry point via RegisterBlock-Door
    CALL "RegisterBlock-Door"
    CALL "GetCallback-BlockInteract" USING STATE-ID INTERACT-PTR

    IF INTERACT-PTR = NULL
        *> Direct entry fallback
        SET INTERACT-PTR TO ENTRY "Callback-Interact"
    END-IF

    IF INTERACT-PTR = NULL
        DISPLAY "ERR: INTERACT-PTR NULL"
        STOP RUN RETURNING 2
    END-IF

    *> Test 1: Lower half interaction (Y=64)
    MOVE 12 TO LK-POSITION-X
    MOVE 64 TO LK-POSITION-Y
    MOVE -35 TO LK-POSITION-Z

    MOVE LK-POSITION-X TO SAVED-X
    MOVE LK-POSITION-Y TO SAVED-Y
    MOVE LK-POSITION-Z TO SAVED-Z

    CALL INTERACT-PTR USING LK-PLAYER LK-ITEM-NAME LK-POSITION LK-FACE LK-CURSOR

    IF LK-POSITION-X NOT = SAVED-X OR LK-POSITION-Y NOT = SAVED-Y OR LK-POSITION-Z NOT = SAVED-Z
        DISPLAY "FAIL_COORD: Y mutated from " SAVED-Y " to " LK-POSITION-Y
        STOP RUN RETURNING 1
    END-IF

    *> Test 2: Upper half interaction (Y=65)
    MOVE 12 TO LK-POSITION-X
    MOVE 65 TO LK-POSITION-Y
    MOVE -35 TO LK-POSITION-Z

    MOVE LK-POSITION-X TO SAVED-X
    MOVE LK-POSITION-Y TO SAVED-Y
    MOVE LK-POSITION-Z TO SAVED-Z

    CALL INTERACT-PTR USING LK-PLAYER LK-ITEM-NAME LK-POSITION LK-FACE LK-CURSOR

    IF LK-POSITION-X NOT = SAVED-X OR LK-POSITION-Y NOT = SAVED-Y OR LK-POSITION-Z NOT = SAVED-Z
        DISPLAY "FAIL_COORD: Y mutated from " SAVED-Y " to " LK-POSITION-Y
        STOP RUN RETURNING 1
    END-IF

    DISPLAY "PASS_COORD"
    STOP RUN RETURNING 0.

END PROGRAM VerifyCoordImmutability.
"""
    harness_path = "/tmp/verify_coord.cob"
    bin_path = "/tmp/verify_coord_bin"
    with open(harness_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(harness_src)

    cobc_cmd = ["cobc", "-x", "-free", "-DGCVERSION=32"] + get_cobc_opts() + [
        "-lstdc++", "-lz", "-o", bin_path, harness_path
    ] + get_all_objects()
    compile_res = subprocess.run(cobc_cmd, cwd=APP_DIR, capture_output=True, text=True)
    assert compile_res.returncode == 0, f"Compilation of coordinate harness failed:\n{compile_res.stderr}"

    run_res = subprocess.run([bin_path], cwd=APP_DIR, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Coordinate immutability check failed:\n{run_res.stdout}\n{run_res.stderr}"
    assert "PASS_COORD" in run_res.stdout

def test_shrinking_property_string_isolation():
    """Verify consecutive property string lookups do not retain trailing bytes."""
    harness_src = """*> Test harness for property string isolation
IDENTIFICATION DIVISION.
PROGRAM-ID. VerifyPropertyIsolation.

DATA DIVISION.
WORKING-STORAGE SECTION.
    COPY DD-BLOCK-STATE REPLACING LEADING ==PREFIX== BY ==TEST-STATE==.
    01 RETRIEVED-VALUE          PIC X(64).
    01 EXPECTED-VALUE           PIC X(64).

PROCEDURE DIVISION.
    MOVE "minecraft:oak_door" TO TEST-STATE-NAME
    MOVE 2 TO TEST-STATE-PROPERTY-COUNT

    MOVE "open" TO TEST-STATE-PROPERTY-NAME(1)
    MOVE "false" TO TEST-STATE-PROPERTY-VALUE(1)

    MOVE "half" TO TEST-STATE-PROPERTY-NAME(2)
    MOVE "lower" TO TEST-STATE-PROPERTY-VALUE(2)

    *> Step 1: Read 'open=false'
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "open" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "false"
        DISPLAY "FAIL_PROP: expected 'false', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 1
    END-IF

    *> Step 2: Transition 'open' from 'false' (5 chars) to 'true' (4 chars)
    MOVE "true" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "open" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "true"
        DISPLAY "FAIL_PROP: trailing byte corruption! expected 'true', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 2
    END-IF

    *> Step 3: Transition 'facing' from 'south' (5 chars) to 'west' (4 chars)
    MOVE "facing" TO TEST-STATE-PROPERTY-NAME(1)
    MOVE "south" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "south"
        DISPLAY "FAIL_PROP: expected 'south', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 3
    END-IF

    MOVE "west" TO TEST-STATE-PROPERTY-VALUE(1)
    INITIALIZE RETRIEVED-VALUE
    CALL "Blocks-Description-GetValue" USING TEST-STATE-DESCRIPTION "facing" RETRIEVED-VALUE
    IF FUNCTION TRIM(RETRIEVED-VALUE) NOT = "west"
        DISPLAY "FAIL_PROP: trailing byte corruption! expected 'west', got '" FUNCTION TRIM(RETRIEVED-VALUE) "'"
        STOP RUN RETURNING 4
    END-IF

    DISPLAY "PASS_PROP"
    STOP RUN RETURNING 0.

END PROGRAM VerifyPropertyIsolation.
"""
    harness_path = "/tmp/verify_prop.cob"
    bin_path = "/tmp/verify_prop_bin"
    with open(harness_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(harness_src)

    cobc_cmd = ["cobc", "-x", "-free", "-DGCVERSION=32"] + get_cobc_opts() + [
        "-lstdc++", "-lz", "-o", bin_path, harness_path
    ] + get_all_objects()
    compile_res = subprocess.run(cobc_cmd, cwd=APP_DIR, capture_output=True, text=True)
    assert compile_res.returncode == 0, f"Compilation of property harness failed:\n{compile_res.stderr}"

    run_res = subprocess.run([bin_path], cwd=APP_DIR, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Property isolation check failed:\n{run_res.stdout}\n{run_res.stderr}"
    assert "PASS_PROP" in run_res.stdout

def test_anti_shortcut():
    """Ensure fixes were applied to core block state modules without hardcoding workarounds."""
    res = subprocess.run(["git", "diff", "HEAD~1", "--name-only"], cwd=APP_DIR, capture_output=True, text=True)
    modified_files = res.stdout.strip().split()

    # Verify no patches to packet handlers
    for f in modified_files:
        assert not f.startswith("src/packets/"), f"Anti-shortcut violation: Upstream packet handler {f} was modified."

    # Verify no hardcoded string literals for bug workarounds in src/
    grep_res = subprocess.run(["git", "grep", "-E", "truee|westh|easth"], cwd=APP_DIR, capture_output=True, text=True)
    assert grep_res.stdout.strip() == "", f"Anti-shortcut violation: Found hardcoded workaround strings:\n{grep_res.stdout}"
