#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='fx_sig_verify',
    version='0.4.10-1',
    license='MPL2',
    description='AWS Lambda to check code signatures.',
    author='Hal Wine',
    author_email='hwine@mozilla.com',
    url='https://github.com/mozilla/fx-sig-verify',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        # uncomment if you test on these interpreters:
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: Stackless',
        # 'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    setup_requires=[
                    ],

    install_requires=[
        "fleece",  ## ==0.15.1",
    ],
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
        'cli': [],
    },
    entry_points={
        'console_scripts': [
            'fx-sig-verify = fx_sig_verify.cli:main [cli]',
            ('print-pe-certs ='
             ' fx_sig_verify.verify_sigs.print_pe_certs:main [cli]'),
            'analyze_cloudwatch = analyze_cloudwatch:main [cli]',
        ],
    },
    scripts=[
        "src/scripts/get-cloudwatch-logs",
        "src/scripts/re-invoke-dirtree",
        "src/scripts/get-and-test-s3-url",
    ],
    dependency_links=[
        ],
)
