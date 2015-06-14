pytest pylint
-------------
.. image:: https://img.shields.io/travis/carsongee/pytest-pylint.svg
    :target: https://travis-ci.org/carsongee/orcoursetrion
.. image:: https://img.shields.io/coveralls/carsongee/pytest-pylint.svg
    :target: https://coveralls.io/r/carsongee/pytest-pylint
.. image:: https://img.shields.io/pypi/v/pytest-pylint.svg
    :target: https://pypi.python.org/pypi/pytest-pylint
.. image:: https://img.shields.io/pypi/dm/pytest-pylint.svg
    :target: https://pypi.python.org/pypi/pytest-pylint
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

   py.test --pylint --pylint-rcfile=/my/pyrc --pylint-error-types=EF

This would use the pylintrc file at /my/pyrc and only error on pylint
Errors and Failures.

Acknowledgements
================

This code is heavily based on 
`pytest-flakes <https://github.com/fschulze/pytest-flakes>`_
