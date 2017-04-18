========
Overview
========

.. attention:: Badges & Automation won't be enabled until merged.

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |requires|
        | |coveralls| |codecov|
    * - package
      - | |version| |downloads| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/ff-sig-verify/badge/?style=flat
    :target: https://readthedocs.org/projects/ff-sig-verify
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/hwine/ff-sig-verify.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/hwine/ff-sig-verify

.. |requires| image:: https://requires.io/github/hwine/ff-sig-verify/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/hwine/ff-sig-verify/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/hwine/ff-sig-verify/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/hwine/ff-sig-verify

.. |codecov| image:: https://codecov.io/github/hwine/ff-sig-verify/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/hwine/ff-sig-verify

.. |version| image:: https://img.shields.io/pypi/v/ff-sig-verify.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/ff-sig-verify

.. |commits-since| image:: https://img.shields.io/github/commits-since/hwine/ff-sig-verify/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/hwine/ff-sig-verify/compare/v0.1.0...master

.. |downloads| image:: https://img.shields.io/pypi/dm/ff-sig-verify.svg
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/ff-sig-verify

.. |wheel| image:: https://img.shields.io/pypi/wheel/ff-sig-verify.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/ff-sig-verify

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/ff-sig-verify.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/ff-sig-verify

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/ff-sig-verify.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/ff-sig-verify


.. end-badges

AWS Lambda to check code signatures.

Installation
============

::

    pip install ff-sig-verify

Documentation
=============

https://ff-sig-verify.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
