#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='xFlow',
    description='A serverless workflow architecture using AWS Lambda functions and Kinesis',
    version='0.1.14',
    packages=['xflow'],
    data_files=[('xflow', ['xflow/schema.yaml'])],
    include_package_data=True,
    extras_require={
        'ruamel': ["ruamel.yaml>=0.11.0,<0.12.0"],
    },
    install_requires=[
        'boto',
        'boto3',
        'bottle',
        'pykwalify==1.5.1',
        'nose',
        'mock',
        'argparse',
        'jsonschema',
        'waitress'
    ],
    author="Jude D'Souza",
    author_email='dsouza_jude@hotmail.com',
    maintainer="Jude D'Souza",
    maintainer_email='dsouza_jude@hotmail.com',
    url='http://github.com/dsouzajude/xFlow',
    download_url='https://github.com/dsouzajude/xflow/archive/0.1.tar.gz',
    entry_points={
        'console_scripts': [
            'xflow = xflow:main',
        ],
    },
    zip_safe=False,
    keywords=[
        'serverless',
        'lambda',
        'kinesis',
        'workflow',
        'streams',
        'eventbus'
    ],
    classifiers=(
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    )
)
