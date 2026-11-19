"""bern: swap a Django swappable model in the middle of a project.

    uvx bern           show what would move (reads only)
    uvx bern apply     move it, in one transaction, after you type the database name
"""

import argparse
import os
import re
import sys
from pathlib import Path

from bernard import animation, core


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    _run_in_project(argv)
    parser = argparse.ArgumentParser(
        prog="bern",
        description="Move the rows of swapped-out Django models into the models that swap "
        "them in: a new shell, the same crab. Nothing is copied, and nothing changes unless everything does.",
    )
    parser.add_argument("command", nargs="?", choices=["plan", "apply"], default="plan",
                        help="plan (default) only reads; apply moves")
    parser.add_argument("--settings", help="settings module (default: $DJANGO_SETTINGS_MODULE, "
                        "then the one manage.py sets)")
    parser.add_argument("--database", default="default", help="database alias (default: default)")
    parser.add_argument("--yes", action="store_true", help="apply without asking, for deploy jobs")
    parser.add_argument("--no-fun", action="store_true", help="skip the animations")
    args = parser.parse_args(argv)
    if not args.no_fun:
        animation.intro()
    _setup(args.settings)
    return _run(args)


def _run_in_project(argv):
    """Under uvx, bern runs in its own environment, without the project's apps: run again
    with the project's Python, bern's own code last on the path so the project's Django wins."""
    python = _project_python()
    if not python or os.environ.get("BERN_IN_PROJECT"):
        return
    os.environ["BERN_IN_PROJECT"] = "1"
    code = "import sys; sys.path.append(sys.argv.pop(1)); from bernard.cli import main; sys.exit(main(sys.argv[1:]))"
    os.execv(python, [str(python), "-c", code, str(Path(__file__).resolve().parent.parent), *argv])


def _project_python():
    """The project's virtualenv Python, unless bern already runs in it."""
    here = Path.cwd()
    candidates = [os.environ.get("VIRTUAL_ENV"), *(d / ".venv" for d in [here, *here.parents])]
    for venv in filter(None, candidates):
        for python in (Path(venv) / "bin" / "python", Path(venv) / "Scripts" / "python.exe"):
            if python.exists():
                return None if Path(venv).resolve() == Path(sys.prefix).resolve() else python
    return None


def _setup(settings):
    sys.path.insert(0, os.getcwd())
    settings = settings or os.environ.get("DJANGO_SETTINGS_MODULE") or _from_manage_py()
    if not settings:
        sys.exit("bern: no Django settings found. Pass --settings, set "
                 "DJANGO_SETTINGS_MODULE, or run bern next to manage.py.")
    os.environ["DJANGO_SETTINGS_MODULE"] = settings
    import django

    try:
        django.setup()
    except ModuleNotFoundError as e:
        sys.exit(f"bern: {e}. Run bern with your project's packages: from its virtualenv, "
                 "or with `uv run --with bern bern`.")


def _from_manage_py():
    manage = Path("manage.py")
    if manage.exists():
        found = re.search(r"DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)", manage.read_text())
        return found and found[1]


def _run(args):
    from django.db import connections

    connection = connections[args.database]
    db_name = os.path.basename(str(connection.settings_dict["NAME"]))
    print(f"bern · {args.command} · {args.database} ({connection.vendor}, {db_name})\n")
    path = str(connection.settings_dict["NAME"])
    if connection.vendor == "sqlite" and ":memory:" not in path and not os.path.exists(path):
        print(f"No database at {path}: nothing to move. (bern never creates one.)")
        return 1
    with connection.cursor() as cursor:
        if not connection.introspection.table_names(cursor):
            print("The database is empty: nothing was ever migrated in it, so nothing to move.")
            return 0
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
              "nothing changes.\nRun `bern apply` to move.")
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
    lines += [f"    record   {'.'.join(key)} as applied" for key in move.records]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
