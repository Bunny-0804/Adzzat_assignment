#!/bin/bash
set -euo pipefail

cd /app

python3 - << 'EOF'
import os

# Fix 1: src/blocks/door.cob
door_file = "src/blocks/door.cob"
if os.path.exists(door_file):
    with open(door_file, "r", encoding="utf-8") as f:
        content = f.read()

    buggy_door = """        IF HALF-VALUE-CLICKED = "upper"
            SUBTRACT 1 FROM LK-POSITION-Y
        ELSE
            ADD 1 TO LK-POSITION-Y
        END-IF
        CALL "World-GetBlock" USING LK-POSITION BLOCK-STATE
        CALL "Blocks-ToDescription" USING BLOCK-STATE OTHER-HALF-DESCRIPTION

        *> Check if the block matches (normally there shouldn't be single-block doors, but just in case)
        IF OTHER-HALF-NAME NOT = CLICKED-NAME
            GOBACK
        END-IF
        CALL "Blocks-Description-GetValue" USING OTHER-HALF-DESCRIPTION "half" HALF-VALUE-OTHER
        IF HALF-VALUE-CLICKED = HALF-VALUE-OTHER
            GOBACK
        END-IF

        *> Toggle the "open" property for the other half
        CALL "Blocks-Description-SetValue" USING OTHER-HALF-DESCRIPTION "open" OPEN-VALUE
        CALL "Blocks-FromDescription" USING OTHER-HALF-DESCRIPTION BLOCK-STATE
        CALL "World-SetBlock" USING PLAYER-CLIENT(LK-PLAYER) LK-POSITION BLOCK-STATE"""

    fixed_door = """        MOVE LK-POSITION TO BLOCK-POSITION
        IF HALF-VALUE-CLICKED = "upper"
            SUBTRACT 1 FROM BLOCK-Y
        ELSE
            ADD 1 TO BLOCK-Y
        END-IF
        CALL "World-GetBlock" USING BLOCK-POSITION BLOCK-STATE
        CALL "Blocks-ToDescription" USING BLOCK-STATE OTHER-HALF-DESCRIPTION

        *> Check if the block matches (normally there shouldn't be single-block doors, but just in case)
        IF OTHER-HALF-NAME NOT = CLICKED-NAME
            GOBACK
        END-IF
        CALL "Blocks-Description-GetValue" USING OTHER-HALF-DESCRIPTION "half" HALF-VALUE-OTHER
        IF HALF-VALUE-CLICKED = HALF-VALUE-OTHER
            GOBACK
        END-IF

        *> Toggle the "open" property for the other half
        CALL "Blocks-Description-SetValue" USING OTHER-HALF-DESCRIPTION "open" OPEN-VALUE
        CALL "Blocks-FromDescription" USING OTHER-HALF-DESCRIPTION BLOCK-STATE
        CALL "World-SetBlock" USING PLAYER-CLIENT(LK-PLAYER) BLOCK-POSITION BLOCK-STATE"""

    if buggy_door in content:
        content = content.replace(buggy_door, fixed_door)
        with open(door_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("Fixed src/blocks/door.cob")

# Fix 2: src/blocks.cob
blocks_file = "src/blocks.cob"
if os.path.exists(blocks_file):
    with open(blocks_file, "r", encoding="utf-8") as f:
        content = f.read()

    buggy_blocks = """WORKING-STORAGE SECTION.
    01 PROPERTY-INDEX           BINARY-LONG UNSIGNED.
    01 SCRATCH-VALUE            PIC X(64).
LINKAGE SECTION.
    COPY DD-BLOCK-STATE REPLACING LEADING ==PREFIX== BY ==LK-STATE==.
    01 LK-PROPERTY-NAME         PIC X ANY LENGTH.
    01 LK-PROPERTY-VALUE        PIC X ANY LENGTH.

PROCEDURE DIVISION USING LK-STATE-DESCRIPTION LK-PROPERTY-NAME LK-PROPERTY-VALUE.
    PERFORM VARYING PROPERTY-INDEX FROM 1 BY 1 UNTIL PROPERTY-INDEX > LK-STATE-PROPERTY-COUNT
        IF LK-PROPERTY-NAME = LK-STATE-PROPERTY-NAME(PROPERTY-INDEX)
            STRING FUNCTION TRIM(LK-STATE-PROPERTY-VALUE(PROPERTY-INDEX)) INTO SCRATCH-VALUE
            MOVE SCRATCH-VALUE TO LK-PROPERTY-VALUE
            EXIT PERFORM
        END-IF
    END-PERFORM"""

    fixed_blocks = """WORKING-STORAGE SECTION.
    01 PROPERTY-INDEX           BINARY-LONG UNSIGNED.
LOCAL-STORAGE SECTION.
    01 SCRATCH-VALUE            PIC X(64).
LINKAGE SECTION.
    COPY DD-BLOCK-STATE REPLACING LEADING ==PREFIX== BY ==LK-STATE==.
    01 LK-PROPERTY-NAME         PIC X ANY LENGTH.
    01 LK-PROPERTY-VALUE        PIC X ANY LENGTH.

PROCEDURE DIVISION USING LK-STATE-DESCRIPTION LK-PROPERTY-NAME LK-PROPERTY-VALUE.
    INITIALIZE SCRATCH-VALUE
    MOVE SPACES TO LK-PROPERTY-VALUE
    PERFORM VARYING PROPERTY-INDEX FROM 1 BY 1 UNTIL PROPERTY-INDEX > LK-STATE-PROPERTY-COUNT
        IF LK-PROPERTY-NAME = LK-STATE-PROPERTY-NAME(PROPERTY-INDEX)
            MOVE LK-STATE-PROPERTY-VALUE(PROPERTY-INDEX) TO LK-PROPERTY-VALUE
            EXIT PERFORM
        END-IF
    END-PERFORM"""

    if buggy_blocks in content:
        content = content.replace(buggy_blocks, fixed_blocks)
        with open(blocks_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("Fixed src/blocks.cob")
EOF

make
make test
