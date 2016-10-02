#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='xFlow',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'boto',
        'boto3',
        'pyyaml>=3.12',
        'nose',
        'mock'
    ],
    entry_points={
        'console_scripts': [
            'xflow = src:main',
        ],
    },
    zip_safe=False,
)
