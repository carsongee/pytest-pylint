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
    version='0.15.1',
    author='Carson Gee',
    author_email='x@carsongee.com',
    url='https://github.com/carsongee/pytest-pylint',
    packages=['pytest_pylint'],
    entry_points={'pytest11': ['pylint = pytest_pylint.plugin']},
    python_requires=">=3.5",
    install_requires=['pytest>=5.0', 'pylint>=2.0.0'],
    setup_requires=['pytest-runner'],
    tests_require=['mock', 'coverage', 'pytest-pep8'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
