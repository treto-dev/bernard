"""`python manage.py bern [plan|apply]`: the bern CLI, for projects with "bernard" in INSTALLED_APPS."""

import argparse

from django.core.management.base import BaseCommand

from bernard import animation, cli


class Command(BaseCommand):
    help = "Move the rows of swapped-out models into the models that swap them in."
    requires_system_checks = []  # the plan runs them, and reports errors as reasons not to move

    def add_arguments(self, parser):
        cli.add_arguments(parser)

    def handle(self, **options):
        if not options["no_fun"]:
            animation.intro()
        if code := cli.run(argparse.Namespace(**options)):
            raise SystemExit(code)
