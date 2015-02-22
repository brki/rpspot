#!/usr/bin/env python
import os
import sys
import environ

if __name__ == "__main__":
    env = environ.Env(DJANGO_SETTINGS_MODULE=(str, 'rpspot.settings.dev'))
    root = environ.Path(__file__) - 1
    env.read_env(root('.env'))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", env('DJANGO_SETTINGS_MODULE'))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
