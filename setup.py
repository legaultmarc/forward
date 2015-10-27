#!/usr/bin/env python
# -*- coding: utf-8 -*-

# How to build source distribution
# python setup.py sdist --format bztar
# python setup.py sdist --format gztar
# python setup.py sdist --format zip

import os
import functools

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


def get_package_data():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    roots = {"templates", "static", os.path.join("tests", "data")}

    excludes = {"forward/static/js/build/.module-cache",
                "forward/static/js/build/.module-cache/manifest"}

    paths = []

    for root in roots:
        root = os.path.join("forward", root)
        for cur, dirs, files in os.walk(root):
            if cur in excludes:
                continue
            join = functools.partial(os.path.join, cur)
            paths.extend(map(join, files))

    # Remove the leading forward.
    paths = [i[8:] for i in paths]

    return paths


def setup_package():
    # Saving the version into a file
    write_version_file()

    setup(
        name="forward",
        version=VERSION,
        description="Tool for gene-based phenomic experiments using cohorts.",
        long_description=("This package facilitates common phenomic analyses "
                          "and automates report creation and data management."
                          ""),
        author=u"Marc-André Legault",
        author_email="legaultmarc@gmail.com",
        url="https://github.com/legaultmarc/forward",
        license="CC BY-NC 4.0",
        packages=find_packages(exclude=["tests", ]),
        package_data={
            "forward": get_package_data()
        },
        entry_points={
            "console_scripts": [
                "forward-cli=forward.scripts.forward_cli:parse_args"
            ],
        },
        classifiers=["Development Status :: 4 - Beta",
                     "Intended Audience :: Developers",
                     "Intended Audience :: Science/Research",
                     "Operating System :: Unix",
                     "Operating System :: MacOS :: MacOS X",
                     "Operating System :: POSIX :: Linux",
                     "Programming Language :: Python",
                     "Programming Language :: Python :: 2.7",
                     "Programming Language :: Python :: 3",
                     "Topic :: Scientific/Engineering :: Bio-Informatics"],
        test_suite="forward.tests.test_suite",
        keywords="bioinformatics genomics phewas epidemiology cohort",
        install_requires=["numpy >= 1.8.1", "pandas >= 0.15",
                          "gepyto >= 0.9.2", "SQLAlchemy >= 0.9.8",
                          "PyYAML >= 3.11", "scipy >= 0.14.0",
                          "Jinja2 >= 2.7.3", "xlrd >= 0.9.3",
                          "six >= 1.9.0", "h5py >= 2.5.0", "pyplink >= 1.0.2",
                          "Pygments >= 2.0.2", "statsmodels >= 0.6.1",
                          "Flask >= 0.10.0", "patsy >= 0.4.0"],
        zip_safe=False
    )


if __name__ == "__main__":
    setup_package()
