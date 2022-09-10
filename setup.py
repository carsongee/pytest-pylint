# -*- coding: utf-8 -*-
"""
pytest-pylint
=============

Plugin for py.test for doing pylint tests
"""

from setuptools import setup

with open("README.rst", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="pytest-pylint",
    description="pytest plugin to check source code with pylint",
    long_description=LONG_DESCRIPTION,
    license="MIT",
    version="0.19.0",
    author="Carson Gee",
    author_email="x@carsongee.com",
    url="https://github.com/carsongee/pytest-pylint",
    packages=["pytest_pylint"],
    entry_points={"pytest11": ["pylint = pytest_pylint.plugin"]},
    python_requires=">=3.7",
    install_requires=["pytest>=5.4", "pylint>=2.3.0", "toml>=0.7.1"],
    setup_requires=["pytest-runner"],
    tests_require=["coverage", "flake8", "black", "isort"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
