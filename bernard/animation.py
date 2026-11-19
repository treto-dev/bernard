"""Bernard l'ermite, the hermit crab: same crab (the rows), new shell (the model).

`intro` walks the crab in before each command; `walk` shows it changing shells after a move.
Both stay quiet outside a terminal, in CI, and with TERM=dumb.
"""

import os
import sys
import time

BERNARD = r"""
                 .-~~~~-.
              .-'  .--.  '-.
             /   .' __ '.   \
            |   /  (  )  \   |
            |   \   ''   /   |
     o   o   \   '.____.'   /
      \ /     '-.        .-'
   ,-( ^ )-.  __/'~~~~~~'
  (_/ \_/ \_)--'
""".strip("\n").splitlines()
LEGS = (r"     /|   |\ ", r"     |\   /| ")  # the two steps of a scuttle
CRAB, SHELL = "🦀", "🐚"  # 2 columns each
GAP = 24
FRAME = 0.06


def intro_frames(distance=36, step=3):
    for i, pad in enumerate(range(distance, -1, -step)):
        yield [" " * pad + line for line in [*BERNARD, LEGS[i % 2]]]


def walk_frames(old, new):
    labels = f"{old[:GAP]:<{GAP + 4}}{new}"
    yield [f"{SHELL}{CRAB}{' ' * GAP}{SHELL}", labels]  # out of the shell, looking around
    for pos in range(2, GAP + 1, 2):
        legs = "  " if pos % 4 else "' "
        trail = (". " * (pos // 2))[: pos - 2] + legs
        yield [f"{SHELL}{trail}{CRAB}{' ' * (GAP - pos)}{SHELL}", labels]
    yield [f"{'  '}{' ' * GAP}{SHELL}{CRAB}", f"{'':<{GAP + 4}}{new} ✓"]  # moved in


def intro(stream=sys.stdout):
    _play(intro_frames(), stream, hold_first=1)


def walk(old, new, stream=sys.stdout):
    _play(walk_frames(old, new), stream, hold_first=8)


def _play(frames, stream, hold_first):
    if not stream.isatty() or os.environ.get("TERM") == "dumb" or os.environ.get("CI"):
        return
    stream.write("\x1b[?25l")  # hide the cursor
    try:
        for i, frame in enumerate(frames):
            if i:
                stream.write(f"\x1b[{len(frame)}F")  # back to the first line of the frame
            stream.write("".join(f"\x1b[2K  {line}\n" for line in frame))
            stream.flush()
            time.sleep(FRAME * (hold_first if i == 0 else 1))
        stream.write("\n")
    finally:
        stream.write("\x1b[?25h")
        stream.flush()
