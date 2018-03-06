import json
import os

from . import Arsa
import click

@click.group()
def arsa():
    pass

@arsa.command('run', short_help='Runs a development server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', default=5000,
              help='The port to bind to.')
# @click.option('--cert', type=CertParamType(),
#               help='Specify a certificate file to use HTTPS.')
# @click.option('--key',
#               type=click.Path(exists=True, dir_okay=False, resolve_path=True),
#               callback=_validate_key, expose_value=False,
#               help='The key file to use when specifying a certificate.')
@click.option('--reload/--no-reload', default=None,
              help='Enable or disable the reloader. By default the reloader '
              'is active if debug is enabled.')
@click.option('--debugger/--no-debugger', default=None,
              help='Enable or disable the debugger. By default the debugger '
              'is active if debug is enabled.')
@click.option('--eager-loading/--lazy-loader', default=None,
              help='Enable or disable eager loading. By default eager '
              'loading is enabled if the reloader is disabled.')
@click.option('--with-threads/--without-threads', default=True,
              help='Enable or disable multithreading.')
def run_command(host, port, reload, debugger, eager_loading,
                with_threads):
    """Run a local development server."""

    from werkzeug.serving import run_simple

    __import__('examples.oracle')

    app = Arsa.create_app()
    run_simple(host, port, app, use_reloader=reload)


def main():
    arsa()

if __name__ == '__main__':
    main()
