#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='arsa',
    version='1.0.0',
    description='Arsa Python SDK',
    author='Corey Collins',
    author_email='corey@trippingrobot.com',
    packages=['arsa'],
    tests_require=['pytest'],
    install_requires=[
        'click>=5.1',
        'Werkzeug>=0.14'
    ],
    entry_points={
        'console_scripts': [
            'arsa = arsa.cli:main',
        ],
    },
)
