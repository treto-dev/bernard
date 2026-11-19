"""With "bernard" in INSTALLED_APPS, a plain `migrate` moves the swapped models first.

List "bernard" before any other app that overrides `migrate`: the first one wins.
DISABLE_BERNARD=1 turns this back into Django's `migrate`.
"""

import argparse

from django.core.management.base import CommandError
from django.core.management.commands.migrate import Command as Migrate
from django.db import connections

from bernard import cli, core

# Anything but a plain `migrate` is left alone: targeted, pretend and read-only runs,
# and the test runner, which passes run_syncdb.
NOT_PLAIN = ("app_label", "migration_name", "fake", "fake_initial", "plan", "check_unapplied",
             "prune", "run_syncdb")


class Command(Migrate):
    def handle(self, *args, **options):
        if not cli.disabled() and not any(options.get(o) for o in NOT_PLAIN):
            _move(options["database"])
        return super().handle(*args, **options)


def _move(using):
    connection = connections[using]
    if cli.missing(connection) or cli.empty(connection):
        return  # a new database: migrate builds it
    moves, problems = core.plan(using)
    if not moves and not problems:
        return  # the usual case, kept silent
    args = argparse.Namespace(command="apply", database=using, yes=True, no_fun=True)
    if cli.run(args):
        raise CommandError("bern could not move the swapped models, so nothing was migrated. "
                           "Set DISABLE_BERNARD=1 to run migrate without it.")
