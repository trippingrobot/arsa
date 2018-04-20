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

def _load_custom_handler(python_path, relpath=None):
    module = '.'.join(python_path.split('.')[:-1])
    klass = python_path.split('.')[-1:]

    if relpath and sys.path[0] != relpath:
        sys.path.insert(0, relpath)

    # Load the handler
    mod = __import__(module, globals(), locals(), klass, 0)
    return getattr(mod, klass[0])

def _get_config(full_path):
    if not os.path.isfile(full_path):
        raise click.ClickException('Configuration file not found {}'.format(full_path))

    config = json.load(open(full_path))

    required = ['handler', 'name', 'stage']

    if not all(key in config for key in required):
        raise click.ClickException('Invalid configuration file.')

    return config

def _find_root_modules(path):
    return [f for f in os.listdir(path) if re.match(r'^.*\.py$', f)]

def _resource_not_found(error):
    code = error.response.get('Error', {}).get('Code', 'Unknown')
    return code == 'ResourceNotFoundException'

def _entity_not_found(error):
    code = error.response.get('Error', {}).get('Code', 'Unknown')
    return code == 'NoSuchEntity'


class DeployCommand(object):

    def __init__(self, config, app, region):
        self.config = _get_config(config)
        self.path = app
        self.stage = self.config['stage']
        self.region = region
        self.build_id = str(uuid.uuid4())

        # Check for credentials
        self.session = boto3.Session(region_name=self.region)
        if self.session.get_credentials() is None:
            raise click.ClickException('No Arsa or AWS credentials were found.')

        # Infrastructure Id's
        self.account_id = self.session.client('sts').get_caller_identity().get('Account')
        self.rest_api_id = None
        self.role_arn = None

    def deploy(self):

        api_name = 'arsa-{}'.format(self.config['name'])

        # Build package into buffer
        buf = self._build()

        # Create IAM Execution Role
        self._setup_role('{}-execution-role'.format(api_name))

        # Create API
        self._setup_api(api_name)

        # Deploy core lambda handler
        main_handler = self.config['handler']
        self._create_lambda('{}:{}'.format(self.account_id, api_name), main_handler, buf)
        source_arn = 'arn:aws:execute-api:{region}:{account_id}:{api_id}/{stage}/*/*'.format(
            region=self.region,
            account_id=self.account_id,
            api_id=self.rest_api_id,
            stage=self.stage
        )
        self._add_lambda_permissions('{}:{}'.format(self.account_id, api_name), source_arn)

        # Setup API proxy resources
        self._setup_resources()

        # Create new API deployment
        self._deploy_api(api_name)

    def _build(self):
        """ build the package """
        click.secho('Building package...', fg='green')

        build_path = os.path.join(os.curdir, '.arsa-build')
        packages = find_packages(where=self.path,
                                 exclude=['tests', 'test']) + _find_root_modules(self.path)

        if os.path.exists(build_path):
            shutil.rmtree(build_path)
        os.makedirs(build_path)

        # install packages
        requirements = self.config.get('requirements', 'requirements.txt')
        fnull = open(os.devnull, 'w')
        subprocess.check_call([
            'pip',
            'install',
            '-r',
            os.path.join(self.path, requirements),
            '-t',
            build_path
        ], stdout=fnull)

        for module in packages:
            src = os.path.join(self.path, module)
            dst = os.path.join(build_path, module)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.pyc'))
            elif os.path.isfile(src):
                shutil.copy(src, dst)

        # zip together for distribution
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as myzip:
            for base, _, files in os.walk(build_path, followlinks=True):
                for file in files:
                    path = os.path.join(base, file)
                    myzip.write(path, path.replace(build_path + '/', ''))

        return buf

    def _create_lambda(self, function_name, handler, buf):
        click.secho('Uploading {} package...'.format(function_name), fg='green')

        lamba_client = self.session.client('lambda')
        try:
            resp = lamba_client.update_function_code(
                FunctionName=function_name,
                ZipFile=buf.getvalue()
            )
            revision_id = resp['RevisionId']
        except ClientError as error:
            if _resource_not_found(error):
                click.secho('Creating new lambda function...', fg='yellow')
                resp = lamba_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.6',
                    Role=self.role_arn,
                    Handler=handler,
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
            Description=self.build_id,
            RevisionId=revision_id
        )
        version_id = resp['Version']

        click.secho('Setting alias to stage...', fg='green')
        try:
            lamba_client.update_alias(
                FunctionName=function_name,
                Name=self.stage,
                FunctionVersion=version_id
            )
        except ClientError as error:
            if _resource_not_found(error):
                click.secho('Creating new alias...', fg='yellow')
                lamba_client.create_alias(
                    FunctionName=function_name,
                    Name=self.stage,
                    FunctionVersion=version_id
                )
            else:
                raise error

    def _add_lambda_permissions(self, function_name, source_arn):
        click.secho('Setting default permissions...', fg='green')
        lamba_client = self.session.client('lambda')
        try:
            lamba_client.get_policy(
                FunctionName='{}:{}'.format(function_name, self.stage),
            )
        except ClientError as error:
            if _resource_not_found(error):
                click.secho('Adding default permissions...', fg='yellow')
                lamba_client.add_permission(
                    FunctionName='{}:{}'.format(function_name, self.stage),
                    StatementId='arsa-statement-permission-{}'.format(self.stage),
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=source_arn
                )
            else:
                raise error


    def _setup_api(self, api_name):
        # Create API Gatway
        api_client = self.session.client('apigateway')
        try:
            apis = api_client.get_rest_apis()
            self.rest_api_id = next(item['id'] for item in apis['items'] if item['name'] == api_name)
        except StopIteration:
            click.secho('Creating new api gateway...', fg='yellow')

            # Create Rest API
            resp = api_client.create_rest_api(
                name=api_name
            )
            self.rest_api_id = resp['id']


    def _setup_role(self, role_name):
         # Create lambda execution role
        iam_client = self.session.client('iam')
        try:
            resp = iam_client.get_role(RoleName=role_name)
            self.role_arn = resp['Role']['Arn']
        except ClientError as error:
            if _entity_not_found(error):
                click.secho('Creating new lambda role...', fg='yellow')
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }

                resp = iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(policy),
                    Description='Arsa lambda execution role'
                )
                self.role_arn = resp['Role']['Arn']
            else:
                raise error

        allowed_actions = self.config.get('allowed_actions', [])
        actions = list(set(['logs:*']) | set(allowed_actions))
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": "*"
                }
            ]
        }

        # Attach role policy for lambda function
        click.secho('Setting permissions to execution role...', fg='green')
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='arsa-lambda-permissions',
            PolicyDocument=json.dumps(policy)
        )

    def _setup_resources(self):
        api_client = self.session.client('apigateway')
        resources = api_client.get_resources(restApiId=self.rest_api_id)
        try:
            # Get resource id
            resource_id = next(item['id'] for item in resources['items'] if item['path'] == '/{proxy+}')
        except StopIteration:
            click.secho('Creating new proxy resource...', fg='yellow')
            parent_id = next(item['id'] for item in resources['items'] if item['path'] == '/')

            # Create proxy resource
            resp = api_client.create_resource(
                restApiId=self.rest_api_id,
                parentId=parent_id,
                pathPart='{proxy+}'
            )
            resource_id = resp['id']

            # Setup ANY method and assign IAM permissions
            # NOTE: If custom permissions are needed, this needs to be changed manually.
            api_client.put_method(
                restApiId=self.rest_api_id,
                resourceId=resource_id,
                httpMethod='ANY',
                authorizationType='AWS_IAM'
            )

            stage_variable = '${stageVariables.lbfunction}'
            api_client.put_integration(
                restApiId=self.rest_api_id,
                resourceId=resource_id,
                httpMethod='ANY',
                integrationHttpMethod='POST',
                type='AWS_PROXY',
                uri='arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:{stage_variable}/invocations'.format(
                    region=self.region,
                    account_id=self.account_id,
                    stage_variable=stage_variable)
            )


    def _deploy_api(self, api_name):
        click.secho('Creating deployment...', fg='green')

        api_client = self.session.client('apigateway')
        api_client.create_deployment(
            restApiId=self.rest_api_id,
            stageName=self.stage,
            variables={
                'lbfunction': '{}:{}'.format(api_name, self.stage)
            }
        )

        click.secho('\nCongratulations your api is deployed at:\n', fg='green')
        click.secho('https://{rest_api_id}.execute-api.{region}.amazonaws.com/{stage}'.format(
            rest_api_id=self.rest_api_id,
            region=self.region,
            stage=self.stage
        ), fg='blue', bold=True)


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
@click.option('--config', '-c', default='arsa.json', help='Your arsa config file"')
@click.option('--app', '-a', default=os.curdir, help='Path to an arsa app if not in root directory.')
@click.option('--handler', '-h', default=None,
              help='Python path to custom request handler.')
def run_command(host, port, config, app, handler):
    """Run a local development server."""

    from werkzeug.serving import run_simple

    if handler:
        handler = _load_custom_handler(handler, relpath=app)

    config = _get_config(config)
    _app = _load_app(config['handler'], relpath=app)

    run_simple(host, port, _app, request_handler=handler)

@arsa.command('deploy', short_help='Deploy your API.')
@click.option('--config', '-c', default='arsa.json', help='Your arsa config file"')
@click.option('--app', '-a', default=os.curdir, help='Path to an arsa app if not in root directory.')
@click.option('--region', default='us-east-1')
def deploy_command(config, app, region):
    cmd = DeployCommand(config, app, region)
    cmd.deploy()

def main():
    """ main method """
    arsa()

if __name__ == '__main__':
    main()
