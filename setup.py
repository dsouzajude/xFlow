#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='xFlow',
    description='A serverless workflow architecture using AWS Lambda functions and Kinesis',
    long_description=readme + '\n\n',
    version='0.1',
    packages=['xflow'],
    data_files = [('.', ['./schema.yaml'])],
    include_package_data=True,
    extras_require={
        'ruamel': ["ruamel.yaml>=0.11.0,<0.12.0"],
    },
    install_requires=[
        'boto',
        'boto3',
        'pykwalify==1.5.1',
        'nose',
        'mock',
        'argparse',
        'waitress'
    ],
    author="Jude D'Souza",
    author_email='dsouza_jude@hotmail.com',
    maintainer="Jude D'Souza",
    maintainer_email='dsouza_jude@hotmail.com',
    url='http://github.com/dsouzajude/xFlow',
    entry_points={
        'console_scripts': [
            'xflow = xflow:main',
        ],
    },
    zip_safe=False,
    classifiers=(
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        'Development Status :: Inactive',
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
