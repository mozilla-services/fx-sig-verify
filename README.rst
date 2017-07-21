========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |travis| |coveralls| |codecov|
    * - package
      - |commits-since|


..
      - | |travis| |requires| |coveralls| |codecov|
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations| |commits-since|

.. |docs| image:: https://readthedocs.org/projects/fx-sig-verify/badge/?style=flat
    :target: https://readthedocs.org/projects/fx-sig-verify
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/mozilla-services/fx-sig-verify.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/mozilla-services/fx-sig-verify

.. |requires| image:: https://requires.io/github/mozilla-services/fx-sig-verify/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/mozilla-services/fx-sig-verify/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/mozilla-services/fx-sig-verify/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/mozilla-services/fx-sig-verify

.. |codecov| image:: https://codecov.io/github/mozilla-services/fx-sig-verify/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/mozilla-services/fx-sig-verify

.. |version| image:: https://img.shields.io/pypi/v/fx-sig-verify.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/fx-sig-verify

.. |commits-since| image:: https://img.shields.io/github/commits-since/mozilla-services/fx-sig-verify/v0.1.1.svg
    :alt: Commits since latest release
    :target: https://github.com/mozilla-services/fx-sig-verify/compare/v0.2.5...master

.. |downloads| image:: https://img.shields.io/pypi/dm/fx-sig-verify.svg
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/fx-sig-verify

.. |wheel| image:: https://img.shields.io/pypi/wheel/fx-sig-verify.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/fx-sig-verify

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/fx-sig-verify.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/fx-sig-verify

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/fx-sig-verify.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/fx-sig-verify


.. end-badges

AWS Lambda to check code signatures.

Installation
============

::

    pip install fx-sig-verify

Documentation
=============

https://fx-sig-verify.readthedocs.io/

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
