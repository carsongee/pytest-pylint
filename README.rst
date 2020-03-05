pytest pylint
-------------
.. image:: https://img.shields.io/travis/carsongee/pytest-pylint.svg
    :target: https://travis-ci.org/carsongee/pytest-pylint
.. image:: https://img.shields.io/coveralls/carsongee/pytest-pylint.svg
    :target: https://coveralls.io/r/carsongee/pytest-pylint
.. image:: https://img.shields.io/pypi/v/pytest-pylint.svg
    :target: https://pypi.python.org/pypi/pytest-pylint
.. image:: https://anaconda.org/conda-forge/pytest-pylint/badges/version.svg
   :target: https://anaconda.org/conda-forge/pytest-pylint
.. image:: https://anaconda.org/conda-forge/pytest-pylint/badges/downloads.svg
    :target: https://anaconda.org/conda-forge/pytest-pylint
.. image:: https://img.shields.io/pypi/l/pytest-pylint.svg
    :target: https://pypi.python.org/pypi/pytest-pylint

Run pylint with pytest and have configurable rule types
(i.e. Convention, Warn, and Error) fail the build.  You can also
specify a pylintrc file.

Sample Usage
============
.. code-block:: shell

   py.test --pylint

would be the most simple usage and would run pylint for all error messages.

.. code-block:: shell

   py.test --pylint --pylint-rcfile=/my/pyrc --pylint-error-types=EF --pylint-jobs=4

This would use the pylintrc file at /my/pyrc, only error on pylint
Errors and Failures, and use 4 cores for running pylint.

You can restrict your test run to only perform pylint checks and not any other
tests by typing:

.. code-block:: shell

    py.test --pylint -m pylint

Acknowledgements
================

This code is heavily based on 
`pytest-flakes <https://github.com/fschulze/pytest-flakes>`__


Releases
========

0.15.1
~~~~~~

- Made `--no-pylint` functional again

0.15.0
~~~~~~

- Added support for Python 3.8 thanks to `yanqd0 <https://github.com/michael-k>`_
- Implemented option to output Pylint results to a reports file thanks to `jose-lpa <https://github.com/jose-lpa>`_
- Refactored into simpler plugin structure


0.14.1
~~~~~~

- Corrected pytest-pylint to properly support ``-p no:cacheprovider``
  thanks to `yanqd0 <https://github.com/yanqd0>`__

0.14.0
~~~~~~

- Added support for Pylint's ignore-patterns for regex based ignores
  thanks to `khokhlin <https://github.com/khokhlin>`__
- pytest-pylint now caches successful pylint checks to speedup test
  reruns when files haven't changed thanks to `yanqd0
  <https://github.com/yanqd0>`__

0.13.0
~~~~~~

- Python 3.7 compatibility verified
- Ignore paths no longer match partial names thanks to `heoga
  <https://github.com/heoga>`__

0.12.3
~~~~~~

- `jamur2 <https://github.com/jamur2>`__ corrected issue where file
  paths where not being output properly on lint failures.

0.12.2
~~~~~~

- Resolved issue where failing files weren't reported thanks to reports from
  `skirpichev <https://github.com/skirpichev>`__ and `jamur2 <https://github.com/jamur2>`__


0.12.1
~~~~~~

- Corrected a bug preventing this plugin from working with py.test >= 3.7.0.

0.12.0
~~~~~~

- `jwkvam <https://github.com/jwkvam>`__ added progress output during linting.

0.11.0
~~~~~~

- Added option ``--no-pylint`` to override ``--pylint`` for cases when
  it's turned on by default.

0.10.0
~~~~~~

- `jwkvam <https://github.com/jwkvam>`__ provided support for pylint 2.0

0.9.0
~~~~~

- `noisecapella <https://github.com/noisecapella>`__ added an option to
  run pylint with multiple processes

0.8.0
~~~~~

- `bdrung <https://github.com/bdrung>`__ corrected inconsitent returns in a function
- Dropped Python 3.3 support

0.7.1
~~~~~

- Corrected path issue reported by `Kargathia <https://github.com/Kargathia>`_

0.7.0
~~~~~

- Linting is performed before tests which enables code duplication
  checks to work along with a performance boost, thanks to @heoga
