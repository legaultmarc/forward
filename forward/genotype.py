# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

from __future__ import division

"""
This module provides utilities to handle genotype data.
"""

import logging
logger = logging.getLogger(__name__)

from gepyto.formats.impute2 import Impute2File
import numpy as np


__all__ = ["Impute2Genotypes"]


class GenotypeDatabaseInterface(object):
    """Abstract class representing the genotypes for the study.

    Genotype databases should support the iterator interface. We will not
    assume that a matrix is available in memory. They will be built if needed
    by the Tasks.

    """
    def __init__(self):
        raise NotImplementedError()

    def extract_variants(self, variant_list):
        raise NotImplementedError()

    def filter_maf(self, maf):
        raise NotImplementedError()

    def filter_completion(self, rate):
        raise NotImplementedError()

    def get_sample_order(self):
        raise NotImplementedError()

class Impute2Genotypes(GenotypeDatabaseInterface):
    def __init__(self, filename, samples, filter_probability=0, **kwargs):
        self.filename = filename
        self.samples = self.load_samples(samples)

        self.impute2file = Impute2File(filename, "dosage",
                                       prob_threshold=filter_probability)

        # Extra arguments could be method calls.
        called_methods = []
        for key, value in kwargs.items():
            if hasattr(self, key):
                getattr(self, key)(value)
                called_methods.append(key)

        for method in called_methods:
            del kwargs[method]

        if kwargs:
            message = "Unrecognized argument or method call: '{}'.".format(
                kwargs
            )
            raise TypeError(message)

        # Filters
        self.thresh_completion = 0
        self.thresh_maf = 0
        self.names = set()
                
    # Context manager interface.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close():
        self.impute2file.close()

    # Iterator interface.
    def __iter__(self):
        return self

    def __next__(self):
        # Get the next vector from the underlying impute2file.
        dosage, info = next(self.impute2file)
        name = info["name"]
        maf = info["maf"]

        # Go through the filters.
        # Name
        if self.names and name not in self.names:
            return self.__next__()

        # MAF
        if maf < self.thresh_maf:
            return self.__next__()  # Invalid, find next...

        # Completion
        if self.thresh_completion != 0:
            completion = np.sum(~np.isnan(dosage)) / dosage.shape[0]
            if completion < self.thresh_completion:
                return self.__next__()

        # Note that probability is already filtered by gepyto.

        return dosage

    next = __next__

    def get_sample_order(self):
        return self.samples

    def load_samples(self, filename):
        logger.info("Loading samples from {}".format(filename))
        with open(filename, "r") as f:
            samples = set([i.rstrip() for i in f])

        return samples

    def filter_completion(self, rate):
        logger.info("Setting the completion threshold to {}".format(rate))
        self.thresh_completion = rate

    def filter_maf(self, maf):
        logger.info("Setting the MAF threshold to {}".format(maf))
        self.thresh_maf = maf

    def filter_name(self, names_list):
        logger.info("Keeping only variants with IDs in file: '{}'".format(
            names_list
        ))
        with open(names_list, "r") as f:
            self.names = set([i.rstrip() for i in f.readlines()])
