"""Bernard l'ermite leaves the old shell (the swapped-out model) and walks into the new one.

Same crab (the rows), new shell (the model): nothing is copied, only the label changes.
"""

import os
import sys
import time

CRAB, SHELL = "🦀", "🐚"  # 2 columns each
GAP = 24
FRAME = 0.06


def frames(old, new):
    labels = f"{old[:GAP]:<{GAP + 4}}{new}"
    yield [f"{SHELL}{CRAB}{' ' * GAP}{SHELL}", labels]  # out of the shell, looking around
    for pos in range(2, GAP + 1, 2):
        legs = "  " if pos % 4 else "' "  # a little scuttle
        trail = (". " * (pos // 2))[: pos - 2] + legs
        yield [f"{SHELL}{trail}{CRAB}{' ' * (GAP - pos)}{SHELL}", labels]
    yield [f"{'  '}{' ' * GAP}{SHELL}{CRAB}", f"{'':<{GAP + 4}}{new} ✓"]  # moved in


def walk(old, new, stream=sys.stdout):
    if not stream.isatty() or os.environ.get("TERM") == "dumb" or os.environ.get("CI"):
        return
    stream.write("\x1b[?25l")  # hide the cursor
    try:
        for i, frame in enumerate(frames(old, new)):
            if i:
                stream.write(f"\x1b[{len(frame)}F")  # back to the first line of the frame
            stream.write("".join(f"\x1b[2K  {line}\n" for line in frame))
            stream.flush()
            time.sleep(FRAME * (8 if i == 0 else 1))
        stream.write("\n")
    finally:
        stream.write("\x1b[?25h")
        stream.flush()
