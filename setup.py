#!/usr/bin/env python
# -*- coding: utf-8 -*-

# How to build source distribution
# python setup.py sdist --format bztar
# python setup.py sdist --format gztar
# python setup.py sdist --format zip

import os

from setuptools import setup, find_packages


MAJOR = 0
MINOR = 1
MICRO = 0
VERSION = "{}.{}.{}".format(MAJOR, MINOR, MICRO)


def write_version_file(fn=None):
    if fn is None:
        fn = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join("forward", "version.py")
        )
    content = ("# THIS FILE WAS GENERATED FROM FORWARD SETUP.PY\n"
               "forward_version = \"{version}\"\n")

    a = open(fn, "w")
    try:
        a.write(content.format(version=VERSION))
    finally:
        a.close()


def setup_package():
    # Saving the version into a file
    write_version_file()

    setup(
        name="forward",
        version=VERSION,
        description="Utilities for pheWAS experiments using cohorts.",
        long_description=("This package facilitates common pheWAS analysis "
                          "and automates report creation and data archiving."),
        author=u"Marc-André Legault",
        author_email="legaultmarc@gmail.com",
        url="https://github.com/legaultmarc/forward",
        license="CC BY-NC 4.0",
        packages=find_packages(exclude=["tests", ]),
        classifiers=["Development Status :: 4 - Beta",
                     "Intended Audience :: Developers",
                     "Intended Audience :: Science/Research",
                     "Operating System :: Unix",
                     "Operating System :: MacOS :: MacOS X",
                     "Operating System :: POSIX :: Linux",
                     "Programming Language :: Python",
                     "Programming Language :: Python :: 2.7",
                     "Topic :: Scientific/Engineering :: Bio-Informatics"],
        test_suite="forward.tests.test_suite",
        keywords="bioinformatics genomics phewas epidemiology cohort",
        install_requires=["numpy >= 1.8.1", "pandas >= 0.15",
                          "gepyto >= 0.9.2", "SQLAlchemy >= 1.0.6"],
    )

    return


if __name__ == "__main__":
    setup_package()
