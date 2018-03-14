#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Arsa command line script"""
import os
import json
import re
import shutil
import zipfile
import sys
import io
import uuid
import subprocess
import click
import boto3
from botocore.exceptions import ClientError
from setuptools import find_packages

from . import __version__ as release

def _find_app(module):
    from . import Arsa

    # Search for the most common names first.
    for attr_name in ('app', 'application'):
        app = getattr(module, attr_name, None)
        if isinstance(app, Arsa):
            return app

    # Otherwise find the only object that is a Arsa instance.
    try:
        app = next(v for k, v in module.__dict__.items() if isinstance(v, Arsa))
        return app
    except StopIteration as error:
        raise click.ClickException(error)


def _load_app(python_path, relpath=None):
    module = '.'.join(python_path.split('.')[:-1])
    func = python_path.split('.')[-1:]

    if relpath and sys.path[0] != relpath:
        sys.path.insert(0, relpath)

    # Load the app
    __import__(module, globals(), locals(), func, 0)

    module_code = sys.modules[module]
    app = _find_app(module_code)

    return app.create_app()

def _get_config(path):
    full_path = os.path.join(path, 'arsa.json')
    if not os.path.isfile(full_path):
        raise click.ClickException('Configuration file not found {}'.format(full_path))

    config = json.load(open(full_path))

    required = ['handler', 'name']

    if all(key not in config for key in required):
        raise click.ClickException('Invalid configuration file.')

    if 'requirements' not in config:
        config['requirements'] = 'requirements.txt'

    return config

def _find_root_modules(path):
    return [f for f in os.listdir(path) if re.match(r'^.*\.py$', f)]

def _resource_not_found(error):
    code = error.response.get('Error', {}).get('Code', 'Unknown')
    return code == 'ResourceNotFoundException'

@click.group()
def arsa():
    """ command group for arsa """
    pass

@arsa.command('config', short_help='Configure project for Arsa.')
@click.option('--path', default=os.curdir, help='Path to an arsa app if not in root directory.')
def run_config(path):
    """ Configure project for Arsa by generating a json configuration """
    name = click.prompt('API Name', default=os.path.basename(os.getcwd()), type=str)
    handler = click.prompt('Handler Function', default='api.handler', type=str)

    # Create requirements file if it doesn't exsit
    full_req_path = os.path.join(path, 'requirements.txt')
    if not os.path.isfile(full_req_path):
        with open(full_req_path, 'w') as reqfile:
            reqfile.write('arsa>={}'.format(release))

    # Create arsa config file if it doesn't exsit
    full_config_path = os.path.join(path, 'arsa.json')
    if not os.path.isfile(full_config_path):
        with open(full_config_path, 'w') as configfile:
            json.dump({"name": name, "handler": handler}, configfile, indent=4)


@arsa.command('run', short_help='Runs a development server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', default=5000,
              help='The port to bind to.')
@click.option('--path', default=os.curdir, help='Path to an arsa app if not in root directory.')
@click.option('--reload/--no-reload', default=None,
              help='Enable or disable the reloader.')
def run_command(host, port, path, reload):
    """Run a local development server."""

    from werkzeug.serving import run_simple

    config = _get_config(path)
    app = _load_app(config['handler'], relpath=path)
    run_simple(host, port, app, use_reloader=reload)

@arsa.command('deploy', short_help='Deploy your API.')
@click.option('--stage', '-s', default='v1',
              help='The stage to deploy your api to e.g. "v1", "production", "canary"')
@click.option('--path', default=os.curdir, help='Path to an arsa app if not in root directory.')
@click.option('--region', default='us-east-1')
def deploy_command(stage, path, region):
    build_id = str(uuid.uuid4())
    build_path = os.path.join(os.curdir, '.arsa-build')

    config = _get_config(path)

    packages = find_packages(where=path, exclude=['tests', 'test']) + _find_root_modules(path)

    # Check for credentials
    session = boto3.Session(region_name=region)
    if session.get_credentials() is None:
        raise click.ClickException('No Arsa or AWS credentials were found.')

    account_id = session.client('sts').get_caller_identity().get('Account')

    # clean out build path
    click.secho('Building package...', fg='green')
    if os.path.exists(build_path):
        shutil.rmtree(build_path)
    os.makedirs(build_path)

    # install packages
    fnull = open(os.devnull, 'w')
    subprocess.check_call([
        'pip',
        'install',
        '-r',
        os.path.join(path, config['requirements']),
        '-t',
        build_path
    ], stdout=fnull)

    for module in packages:
        src = os.path.join(path, module)
        dst = os.path.join(build_path, module)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.pyc'))
        else:
            shutil.copy(src, dst)



    # zip together for distribution
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as myzip:
        for base, _, files in os.walk(build_path, followlinks=True):
            for file in files:
                path = os.path.join(base, file)
                myzip.write(path, path.replace(build_path + '/', ''))


    lamba_client = session.client('lambda')
    function_name = '{}:arsa-{}'.format(account_id, config['name'])

    # Upload package
    click.secho('Uploading package...', fg='green')
    try:
        resp = lamba_client.update_function_code(
            FunctionName=function_name,
            ZipFile=buf.getvalue()
        )
        revision_id = resp['RevisionId']
    except ClientError as error:
        if _resource_not_found(error):
            resp = lamba_client.create_function(
                FunctionName=function_name,
                Runtime='python3.6',
                Role='arn:aws:iam::909533743566:role/development-lambda_exec_role',
                Handler=config['handler'],
                Code={
                    'ZipFile': buf.getvalue()
                }
            )
            revision_id = resp['RevisionId']
        else:
            raise error

    # Publish version
    click.secho('Publishing lambda function...', fg='green')
    resp = lamba_client.publish_version(
        FunctionName=function_name,
        Description=build_id,
        RevisionId=revision_id
    )
    version_id = resp['Version']

    click.secho('Creating alias to stage...', fg='green')
    try:
        lamba_client.update_alias(
            FunctionName=function_name,
            Name=stage,
            FunctionVersion=version_id
        )
    except ClientError as error:
        if _resource_not_found(error):
            lamba_client.create_alias(
                FunctionName=function_name,
                Name=stage,
                FunctionVersion=version_id
            )
        else:
            raise error

    api_client = session.client('apigateway')
    api_name = 'arsa-{}'.format(config['name'])

    try:
        apis = api_client.get_rest_apis()
        rest_api_id = next(item['id'] for item in apis['items'] if item['name'] == api_name)
    except StopIteration:
        click.secho('Creating new api gateway...', fg='yellow')

        # Create Rest API
        resp = api_client.create_rest_api(
            name=api_name
        )
        rest_api_id = resp['id']


    resources = api_client.get_resources(restApiId=rest_api_id)
    try:
        # Get resource id
        resource_id = next(item['id'] for item in resources['items'] if item['path'] == '/{proxy+}')
    except StopIteration:
        click.secho('Creating new proxy resource...', fg='yellow')
        parent_id = next(item['id'] for item in resources['items'] if item['path'] == '/')

        # Create proxy resource
        resp = api_client.create_resource(
            restApiId=rest_api_id,
            parentId=parent_id,
            pathPart='{proxy+}'
        )
        resource_id = resp['id']

        # Setup ANY method
        resp = api_client.put_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='ANY',
            authorizationType='NONE'
        )

        stage_variable = '${stageVariables.lbfunction}'
        api_client.put_integration(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod='ANY',
            integrationHttpMethod='POST',
            type='AWS_PROXY',
            uri='arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:{stage_variable}/invocations'.format(
                region=region,
                account_id=account_id,
                stage_variable=stage_variable)
        )

    click.secho('Creating deployment...', fg='green')
    api_client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage,
        variables={
            'lbfunction': '{}:{}'.format(api_name, stage)
        }
    )

    click.secho('\nCongratulations your api is deployed at:\n', fg='green')
    click.secho('https://{rest_api_id}.execute-api.{region}.amazonaws.com/{stage}'.format(
        rest_api_id=rest_api_id,
        region=region,
        stage=stage
    ), fg='blue', bold=True)

def main():
    """ main method """
    arsa()

if __name__ == '__main__':
    main()
