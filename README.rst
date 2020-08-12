========
Overview
========


Documentation for this project is currently maintained restructured text format.
A rendered version is available at https://fx-sig-verify.readthedocs.io/en/latest/ or read the source in the docs__ directory.

If you are just looking to run the scripts locally, use the
`Dockerfile.dev-environment`_ to build a docker image to use. VS-Code will
offer to do that for you. This is the recommended way to manually check
binaries.

__ docs/

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |travis| |coveralls| |codecov|
    * - version status
      - |commits-since|


..
      - | |travis| |requires| |coveralls| |codecov|
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations| |commits-since|

.. |docs| image:: https://readthedocs.org/projects/fx-sig-verify/badge/?style=flat
    :target: https://fx-sig-verify.readthedocs.io/fx-sig-verify
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

.. |commits-since| image:: https://img.shields.io/github/commits-since/mozilla-services/fx-sig-verify/v0.4.10.svg
    :alt: Commits since latest release
    :target: https://github.com/mozilla-services/fx-sig-verify/compare/v0.4.10...master

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

.. _Dockerfile.dev-environment: ./Dockerfile.dev-environment
