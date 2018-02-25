import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

setup(name='arsa-sdk',
      version='1.0',
      description='Arsa Python SDK',
      author='Corey Collins',
      author_email='coreyecollins@gmail.com',
      packages=find_packages(exclude=['test', 'test.*']),
      tests_require=['pytest'],
      install_requires=[
          'boto3'
          ]
)
