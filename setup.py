import os
import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 4):
    raise RuntimeError("requires Python 3.4 or newer")

import pybench

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pybench-mongodb',
    version=pybench.__version__,
    description="MongoDB Benchmarks in Python",
    long_description=long_description,
    url='https://github.com/peterschwaller/pybench-mongodb',

    author='Peter Schwaller',
    author_email='peter.schwaller@percona.com',
    license='All rights reserved by author, proprietary and restricted.',

    packages=find_packages(exclude=['tests']),
    install_requires=[
        'appdirs',
        'hjson',
        'ijson',
        'pymongo',
    ],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    package_data={
        '': ['examples/*']
    },
    entry_points={
        'console_scripts': [
            'pybench-mongodb=pybench.main:main',
        ],
    },
    classifiers=[
        'Private :: Do Not Upload',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Environment :: Plugins',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Database :: Front-Ends',
        'Topic :: Games/Entertainment',
    ],
    setup_requires=[
        'pytest-runner',
        'setuptools-pep8',
        'setuptools-lint',
    ],
)
