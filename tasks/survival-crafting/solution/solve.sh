#!/bin/bash
set -euo pipefail

cd /app

python3 - << 'EOF'
import os

# 1. Restore src/inventory/inventory.cob
inv_file = "src/inventory/inventory.cob"
if os.path.exists(inv_file):
    with open(inv_file, "r", encoding="utf-8") as f:
        content = f.read()

    stripped_body = """PROCEDURE DIVISION USING LK-INVENTORY-LENGTH LK-INVENTORY LK-INPUT-COUNT LK-INPUT-START LK-OUTPUT-SLOT.
    *> Stripped crafting output calculation
    MOVE 0 TO LK-SLOT-COUNT(LK-OUTPUT-SLOT + 1)
    GOBACK."""

    full_body = """PROCEDURE DIVISION USING LK-INVENTORY-LENGTH LK-INVENTORY LK-INPUT-COUNT LK-INPUT-START LK-OUTPUT-SLOT.
    INITIALIZE INITIAL-GRID
    IF LK-INPUT-COUNT = 4
        IF LK-SLOT-COUNT(LK-INPUT-START + 1) > 0
            MOVE LK-SLOT-ID(LK-INPUT-START + 1) TO INITIAL-GRID-ID(1)
        END-IF
        IF LK-SLOT-COUNT(LK-INPUT-START + 2) > 0
            MOVE LK-SLOT-ID(LK-INPUT-START + 2) TO INITIAL-GRID-ID(2)
        END-IF
        IF LK-SLOT-COUNT(LK-INPUT-START + 3) > 0
            MOVE LK-SLOT-ID(LK-INPUT-START + 3) TO INITIAL-GRID-ID(4)
        END-IF
        IF LK-SLOT-COUNT(LK-INPUT-START + 4) > 0
            MOVE LK-SLOT-ID(LK-INPUT-START + 4) TO INITIAL-GRID-ID(5)
        END-IF
    ELSE
        PERFORM VARYING SLOT FROM 1 BY 1 UNTIL SLOT > LK-INPUT-COUNT
            IF LK-SLOT-COUNT(LK-INPUT-START + SLOT) > 0
                MOVE LK-SLOT-ID(LK-INPUT-START + SLOT) TO INITIAL-GRID-ID(SLOT)
            END-IF
        END-PERFORM
    END-IF

    MOVE INITIAL-GRID TO CRAFTING-GRID
    PERFORM MatchShapelessRecipes

    MOVE INITIAL-GRID TO CRAFTING-GRID
    PERFORM MatchShapedRecipes

    *> No matching recipe found - clear the output slot
    MOVE 0 TO LK-SLOT-COUNT(LK-OUTPUT-SLOT + 1)

    GOBACK."""

    if stripped_body in content:
        content = content.replace(stripped_body, full_body)
        with open(inv_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("Restored src/inventory/inventory.cob")

# 2. Restore src/inventory/window-crafting.cob
wcraft_file = "src/inventory/window-crafting.cob"
if os.path.exists(wcraft_file):
    with open(wcraft_file, "r", encoding="utf-8") as f:
        content = f.read()

    stripped_wcraft = """            WHEN 1 THRU 9 *> crafting input
                MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)"""

    fixed_wcraft = """            WHEN 0 *> crafting output
                IF PLAYER-WINDOW-SLOT-COUNT(LK-PLAYER, 1) > 0 AND LK-SLOT-COUNT = 0
                    MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, 1)
                    PERFORM VARYING SLOT FROM 1 BY 1 UNTIL SLOT > 9
                        IF PLAYER-WINDOW-SLOT-COUNT(LK-PLAYER, SLOT + 1) > 0
                            SUBTRACT 1 FROM PLAYER-WINDOW-SLOT-COUNT(LK-PLAYER, SLOT + 1)
                        END-IF
                    END-PERFORM
                    CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH PLAYER-WINDOW-SLOTS(LK-PLAYER)
                        CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                    MOVE 1 TO LK-SYNC-REQUIRED
                ELSE
                    MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)
                END-IF

            WHEN 1 THRU 9 *> crafting input
                MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)
                CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH PLAYER-WINDOW-SLOTS(LK-PLAYER)
                    CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                MOVE 1 TO LK-SYNC-REQUIRED"""

    # Replace both WHEN 0 and WHEN 1 THRU 9
    old_block = """            WHEN 0 *> crafting output
                MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)

            WHEN 1 THRU 9 *> crafting input
                MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)"""

    if old_block in content:
        content = content.replace(old_block, fixed_wcraft)
    elif stripped_wcraft in content:
        content = content.replace(stripped_wcraft, """            WHEN 1 THRU 9 *> crafting input
                MOVE LK-SLOT TO PLAYER-WINDOW-SLOT(LK-PLAYER, LK-INDEX + 1)
                CALL "Inventory-UpdateCraftingOutput" USING WINDOW-INVENTORY-LENGTH PLAYER-WINDOW-SLOTS(LK-PLAYER)
                    CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                MOVE 1 TO LK-SYNC-REQUIRED""")

    with open(wcraft_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Restored src/inventory/window-crafting.cob")

# 3. Restore src/inventory/window-player.cob
wplayer_file = "src/inventory/window-player.cob"
if os.path.exists(wplayer_file):
    with open(wplayer_file, "r", encoding="utf-8") as f:
        content = f.read()

    stripped_wplayer = """            WHEN 1 THRU 4 *> crafting input
                 MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)"""

    fixed_wplayer = """            WHEN 0 *> crafting output
                IF PLAYER-INVENTORY-SLOT-COUNT(LK-PLAYER, 1) > 0 AND LK-SLOT-COUNT = 0
                    MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, 1)
                    PERFORM VARYING SLOT FROM 1 BY 1 UNTIL SLOT > 4
                        IF PLAYER-INVENTORY-SLOT-COUNT(LK-PLAYER, SLOT + 1) > 0
                            SUBTRACT 1 FROM PLAYER-INVENTORY-SLOT-COUNT(LK-PLAYER, SLOT + 1)
                        END-IF
                    END-PERFORM
                    CALL "Inventory-UpdateCraftingOutput" USING PLAYER-INVENTORY-LENGTH PLAYER-INVENTORY(LK-PLAYER)
                        CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                    MOVE 1 TO LK-SYNC-REQUIRED
                ELSE
                    MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)
                END-IF

            WHEN 1 THRU 4 *> crafting input
                MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)
                CALL "Inventory-UpdateCraftingOutput" USING PLAYER-INVENTORY-LENGTH PLAYER-INVENTORY(LK-PLAYER)
                    CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                MOVE 1 TO LK-SYNC-REQUIRED"""

    old_player_block = """            WHEN 0 *> crafting output
                 MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)

            WHEN 1 THRU 4 *> crafting input
                 MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)"""

    if old_player_block in content:
        content = content.replace(old_player_block, fixed_wplayer)
    elif stripped_wplayer in content:
        content = content.replace(stripped_wplayer, """            WHEN 1 THRU 4 *> crafting input
                MOVE LK-SLOT TO PLAYER-INVENTORY-SLOT(LK-PLAYER, LK-INDEX + 1)
                CALL "Inventory-UpdateCraftingOutput" USING PLAYER-INVENTORY-LENGTH PLAYER-INVENTORY(LK-PLAYER)
                    CRAFTING-GRID-SIZE CRAFTING-GRID-START CRAFTING-OUTPUT-SLOT
                MOVE 1 TO LK-SYNC-REQUIRED""")

    # Also ensure UpdateCrafting in window-player uses PLAYER-INVENTORY(LK-PLAYER)
    content = content.replace(
        'USING WINDOW-INVENTORY-LENGTH PLAYER-WINDOW-SLOTS(LK-PLAYER)',
        'USING PLAYER-INVENTORY-LENGTH PLAYER-INVENTORY(LK-PLAYER)'
    )

    with open(wplayer_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Restored src/inventory/window-player.cob")
EOF

make
make test
