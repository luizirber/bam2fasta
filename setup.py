from __future__ import print_function
from setuptools import setup, find_packages
import os


EXTRA_LINK_ARGS = []
NAME = 'bam2fasta'
PACKAGES = find_packages()
META_PATH = os.path.join('bam2fasta', '__init__.py')
KEYWORDS = [
    '10x', 'bam',
    'genomic', 'fastas',
    'kmers',
    'sequences'
]

CLASSIFIERS = [
    "Environment :: Console",
    "Environment :: MacOS X",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Programming Language :: C++",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]

CLASSIFIERS.append("Development Status :: 5 - Production/Stable")

with open('README.md', 'r') as readme:
    LONG_DESCRIPTION = readme.read()

SETUP_METADATA = \
    {
        "name": "bam2fasta",
        "description": "tool for converting a bam file to fastas for each barcode",
        "long_description": LONG_DESCRIPTION,
        "long_description_content_type": "text/markdown",
        "url": "https://github.com/pranathivemuri/bam2fasta",
        "author": "Pranathi Vemuri",
        "author_email": "pranathi93.vemuri@gmail.com",
        "maintainer": "Pranathi Vemuri",
        "maintainer_email": "pranathi93.vemuri@gmail.com",
        "license": "BSD 3-clause",
        "packages": find_packages(exclude=["tests", "benchmarks"]),
        "entry_points": {'console_scripts': [
            'bam2fasta = bam2fasta.__main__:main']},
        "install_requires": ["screed>=0.9", "pathos==0.2.5", "pysam==0.15.3", "tqdm==4.36.1"],
        "setup_requires": ["setuptools>=38.6.0",
                           'setuptools_scm', 'setuptools_scm_git_archive'],
        "extras_require": {
            'test': ['pytest', 'pytest-cov', 'numpy', 'matplotlib', 'scipy', 'recommonmark'],
            'demo': ['jupyter', 'jupyter_client', 'ipython'],
        },
        "classifiers": CLASSIFIERS
    }

setup(**SETUP_METADATA)
