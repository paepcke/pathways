import multiprocessing
from setuptools import setup, find_packages
import os
import glob

datafiles = ['src/pathways/courseNameAcademicOrg.csv',
             'src/pathways/crsNmDescriptions.csv'
             ]

setup(
    name = "pathways",
    version = "0.1",
    packages = find_packages(),

    # Dependencies on other packages:
    # Couldn't get numpy install to work without
    # an out-of-band: sudo apt-get install python-dev
    setup_requires   = [],
    install_requires = ['matplotlib>=2.2.3',
                        'numpy>=1.15.0',
                        'scikit-learn>=0.20.0',
                        #***'PyQt5>=5.11.2',
                        'PyQt5>=5.13.1',
                        'dill>=0.2.8.2',
                        'cffi>=1.11.5',
                        'gensim>=3.6.0',
                        'pysqlite3>=0.2.0',
                        'configparser>=3.3.0',
                        'MulticoreTSNE>=0.0.1.1',
                        'requests>=2.21.0',
                        'pandas>=0.25.1',
                        'nltk>=3.4.5',
                        'wordcloud>=1.5.0',
                        'networkx>=2.3',
                        ],

    #dependency_links = ['https://github.com/DmitryUlyanov/Multicore-TSNE/tarball/master#egg=package-1.0']
    # Unit tests; they are initiated via 'python setup.py test'
    test_suite       = 'nose.collector', 
    tests_require    =['nose'],

    # metadata for upload to PyPI
    author = "Andreas Paepcke",
    author_email = "paepcke@cs.stanford.edu",
    description = "Analysis of college pathways.",
    license = "BSD",
    keywords = "MySQL",
    url = "git@github.com:paepcke/pathways.git",   # project home page, if any
)
