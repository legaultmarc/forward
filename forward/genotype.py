# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides utilities to handle genotype data.
"""

from gepyto.formats.impute2 import Impute2File


__all__ = ["Impute2Genotypes"]


class GenotypeDatabaseInterface(object):
    """Abstract class representing the genotypes for the study."""
    def __init__(self):
        raise NotImplementedError()

    def extract_variants(self, variant_list):
        raise NotImplementedError()

class Impute2Genotypes(GenotypeDatabaseInterface):
    def __init__(self, filename, samples):
        self.filename = filename
        self.samples = samples
