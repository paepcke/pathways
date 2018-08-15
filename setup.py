import multiprocessing
from setuptools import setup, find_packages
import os
import glob

datafiles = ['src/pathways/courseNameAcademicOrg.csv']

setup(
    name = "pathways",
    version = "0.1",
    packages = find_packages(),

    # Dependencies on other packages:
    # Couldn't get numpy install to work without
    # an out-of-band: sudo apt-get install python-dev
    setup_requires   = [],
    install_requires = ['matplotlib>=2.2.3',
			'configparser>=3.3.0',
			],

    #dependency_links = ['https://github.com/DmitryUlyanov/Multicore-TSNE/tarball/master#egg=package-1.0']
    # Unit tests; they are initiated via 'python setup.py test'
    test_suite       = 'nose.collector', 

    # metadata for upload to PyPI
    author = "Andreas Paepcke",
    author_email = "paepcke@cs.stanford.edu",
    description = "Thin wrapper around pymysql. Provides Python iterator for queries. Abstracts away cursor.",
    license = "BSD",
    keywords = "MySQL",
    url = "https://github.com/paepcke/pymysql_utils",   # project home page, if any
)
