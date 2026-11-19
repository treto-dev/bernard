"""bernard: swap a Django swappable model in the middle of a project.

    bernard            show what would move (reads only)
    bernard apply      move it, in one transaction, after you type the database name
"""

import argparse
import os
import re
import sys
from pathlib import Path

from bernard import animation, core


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="bernard",
        description="Move the rows of swapped-out Django models into the models that swap "
        "them in: a new shell, the same crab. Nothing is copied, and nothing changes unless everything does.",
    )
    parser.add_argument("command", nargs="?", choices=["plan", "apply"], default="plan",
                        help="plan (default) only reads; apply moves")
    parser.add_argument("--settings", help="settings module (default: $DJANGO_SETTINGS_MODULE, "
                        "then the one manage.py sets)")
    parser.add_argument("--database", default="default", help="database alias (default: default)")
    parser.add_argument("--yes", action="store_true", help="apply without asking, for deploy jobs")
    parser.add_argument("--no-fun", action="store_true", help="skip the animation")
    args = parser.parse_args(argv)
    _setup(args.settings)
    return _run(args)


def _setup(settings):
    sys.path.insert(0, os.getcwd())
    settings = settings or os.environ.get("DJANGO_SETTINGS_MODULE") or _from_manage_py()
    if not settings:
        sys.exit("bernard: no Django settings found. Pass --settings, set "
                 "DJANGO_SETTINGS_MODULE, or run bernard next to manage.py.")
    os.environ["DJANGO_SETTINGS_MODULE"] = settings
    import django

    django.setup()


def _from_manage_py():
    manage = Path("manage.py")
    if manage.exists():
        found = re.search(r"DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)", manage.read_text())
        return found and found[1]


def _run(args):
    from django.db import connections

    connection = connections[args.database]
    db_name = os.path.basename(str(connection.settings_dict["NAME"]))
    print(f"bernard · {args.command} · {args.database} ({connection.vendor}, {db_name})\n")
    moves, problems = core.plan(args.database)
    for move in moves:
        print(describe(move))
    if problems:
        print("Bernard stays in the old shell:", *(f"  - {p}" for p in problems), sep="\n")
        return 1
    if not moves:
        print("Nothing to move: every swapped-in model already has its tables.")
        return 0
    if args.command == "plan":
        print("No row is copied, and it all runs in one transaction: if any step fails, "
              "nothing changes.\nRun `bernard apply` to move.")
        return 0
    if not args.yes and not _confirmed(db_name):
        print("Not confirmed: nothing changed.")
        return 1
    try:
        core.apply(moves, args.database)
    except core.Refused as e:
        print(f"Nothing changed: {e}")
        return 1
    except BaseException:
        print("Nothing changed: the transaction was rolled back.", file=sys.stderr)
        raise
    rows = sum(m.rows for m in moves)
    if not args.no_fun:
        animation.walk(", ".join(m.old for m in moves), ", ".join(m.new for m in moves))
    print(f"Done: {', '.join(m.new for m in moves)} moved in ({_rows(rows)}, none copied). "
          "Run `migrate` next.")
    return 0


def _confirmed(db_name):
    if not sys.stdin.isatty():
        print("No terminal to confirm in: pass --yes to apply.")
        return False
    return input(f"Type the database name ({db_name}) to move: ").strip() == db_name


def _rows(n):
    return f"{n:,} row{'s' if n != 1 else ''}"


def describe(move):
    width = max([len(a) for a, _ in move.renames] or [0])
    lines = [f"  {move.old} → {move.new}   ({move.setting}, {_rows(move.rows)})"]
    lines += [f"    drop     {t}  (empty, made by an earlier migrate)" for t in move.drops]
    lines += [f"    rename   {a:<{width}}  →  {b}" for a, b in move.renames]
    lines += [f"    create   {t}" for t in move.creates]
    lines += [f"    alter    {t}.{c}  {a} → {b}" for t, c, a, b in move.alters]
    lines += [f"    add      {kind} {t}.{name}" for t, kind, name in move.adds]
    lines += [f"    relabel  {oa}.{om} → {na}.{nm}" for oa, om, na, nm in move.relabels]
    lines.append(f"    record   {'.'.join(move.migration)} as applied")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
