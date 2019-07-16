# -*- coding: utf-8 -*-
"""
pytest-pylint
=============

Plugin for py.test for doing pylint tests
"""

from setuptools import setup

setup(
    name='pytest-pylint',
    description='pytest plugin to check source code with pylint',
    long_description=open("README.rst").read(),
    license='MIT',
    version='0.14.1',
    author='Carson Gee',
    author_email='x@carsongee.com',
    url='https://github.com/carsongee/pytest-pylint',
    py_modules=['pytest_pylint'],
    entry_points={'pytest11': ['pylint = pytest_pylint']},
    install_requires=['pytest>=2.7', 'pylint>=1.4.5', 'six'],
    setup_requires=['pytest-runner'],
    tests_require=['mock', 'coverage', 'pytest-pep8'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
