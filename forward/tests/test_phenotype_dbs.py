# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the Phenotype databases implementations.
"""

from pkg_resources import resource_filename
import unittest

from ..phenotype.db import ExcelPhenotypeDatabase
from .abstract_tests import TestAbstractPhenDB
from . import dummies


class TestExcelPhenotypeDatabase(TestAbstractPhenDB, unittest.TestCase):
    """Tests for ExcelPhenotypeDatabase."""
    def setUp(self):
        super(TestExcelPhenotypeDatabase, self).setUp()
        self.db = ExcelPhenotypeDatabase(
            resource_filename(__name__, "data/test_excel_db.xlsx"),
            "sample", missing_values="-9"
        )
        self._variables = ["qte1", "discrete1", "qte2", "discrete2", "covar"]


class TestDummyPhenotypeDatabase(TestAbstractPhenDB, unittest.TestCase):
    """Tests for DummyPhenDB."""
    def setUp(self):
        super(TestDummyPhenotypeDatabase, self).setUp()
        self.db = dummies.DummyPhenDatabase()
        self._variables = ["var1", "var2", "var3", "var4", "var5", "var6"]
