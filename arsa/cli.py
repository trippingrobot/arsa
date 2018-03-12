#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Arsa command line script"""
import os
import sys
import click
import boto3
from modulefinder import ModuleFinder

from . import Arsa
from .exceptions import NoCredentailsFoundError

def setup_path(path):
    """Given a filename this will try to calculate the python path, add it
    to the search path and return the actual module name that is expected.
    """
    path = os.path.realpath(path)

    # remove py extension
    if os.path.splitext(path)[1] == '.py':
        path = os.path.splitext(path)[0]

    # Check to see if __init__ is in the path
    if os.path.basename(path) == '__init__':
        path = os.path.dirname(path)

    module_name = []

    # move up until outside package structure (no __init__.py)
    while True:
        path, name = os.path.split(path)
        module_name.append(name)

        if not os.path.exists(os.path.join(path, '__init__.py')):
            break

    if sys.path[0] != path:
        sys.path.insert(0, path)

    return '.'.join(module_name[::-1])


@click.group()
def arsa():
    """ command group for arsa """
    pass

@arsa.command('run', short_help='Runs a development server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', default=5000,
              help='The port to bind to.')
@click.option('--path', default='handler.py',
              help='The path to the file or module containing the arsa configuration.')
@click.option('--reload/--no-reload', default=None,
              help='Enable or disable the reloader.')
def run_command(host, port, path, reload):
    """Run a local development server."""

    from werkzeug.serving import run_simple

    import_path = setup_path(path)
    __import__(import_path)

    app = Arsa.create_app()
    run_simple(host, port, app, use_reloader=reload)

@arsa.command('deploy', short_help='Deploy your API.')
@click.option('--stage', '-s', default='v1',
              help='The stage to deploy your api to e.g. "v1", "production", "canary"')
@click.option('--path', default='handler.py',
              help='The path to the file or module containing the arsa configuration.')
@click.option('--region', default='us-east-1')
def deploy_command(stage, path, region):

    # TODO: Load the configuration
    name = 'app_name'
    modules = []

    # Load the app
    import_path = setup_path(path)
    __import__(import_path)

    app = Arsa()

    # Check for credentials
    session = boto3.Session(region_name=region)
    if session.get_credentials() is None:
        raise click.ClickException('No Arsa or AWS credentials were found.')

    # TODO: Build package. Will install dependencys+arsa into .arsa-build folder
        # TODO: mkdir -p .arsa-build
        # TODO: pip install <dep> -t .arsa-build/
        # TODO: copy any local python packages and files
        # TODO: zip pacakge

    # TODO: Upload package
    # TODO: Create or update Lambda function
    # TODO: Create API Gateway api if doesn't exist.
    # TODO: Create or update stage
    # TODO: Create or update stage variables

    # TODO: Create an api resource for each
    routes = app.factory.get_rules({})
    for route in routes:
        print(route.rule)

    # TODO: Deploy to stage

def main():
    """ main method """
    arsa()

if __name__ == '__main__':
    main()
