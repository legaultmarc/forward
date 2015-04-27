# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

from __future__ import division
try:
    # Python2
    range = xrange
except NameError:
    pass

"""
This module provides utilities to handle genotype data.
"""

import collections
import logging
logger = logging.getLogger(__name__)

from gepyto.formats.impute2 import Impute2File
import numpy as np
import pandas as pd
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.ext.hybrid import hybrid_property


from . import SQLAlchemyBase

__all__ = ["MemoryImpute2Geno"]


class FrozenDatabaseError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return ("Once initialized, genotype databases are immutable. Further "
                "filtering needs to be done at the Task level.")


class Variant(SQLAlchemyBase):
    __tablename__ = "variants"

    name = Column(String(25), primary_key=True)
    chrom = Column(String(15))
    pos = Column(Integer)
    mac = Column(Float)  # Minor allele count can be approximated using dosage.
    n_missing = Column(Integer)
    n_non_missing = Column(Integer)

    # The maf = mac / n_non_missing
    @hybrid_property
    def maf(self):
        return self.mac / self.n_non_missing

    # The completion rate = n_non_missing / (n_non_missing + n_missing)
    @hybrid_property
    def completion_rate(self):
        return self.n_non_missing / (self.n_non_missing + self.n_missing)


class GenotypeDatabaseInterface(object):
    """Abstract class representing the genotypes for the study.

    Genotype databases should support the iterator interface. We will not
    assume that a matrix is available in memory. They will be built if needed
    by the Tasks.

    """
    def __init__(self):
        raise NotImplementedError()

    # Sample management interface.
    def get_sample_order(self):
        """Return a list of the (ordered) samples as represented in the
           database.

        """
        return self.samples

    def load_samples(self, filename):
        """Read a list of samples from a single column file."""
        logger.info("Loading samples from {}".format(filename))
        with open(filename, "r") as f:
            samples = [i.rstrip() for i in f]

        self.samples = np.array(samples, dtype=str)

    # Interrogate the variant database.
    def query_variants(self, session):
        return session.query(Variant)

    # Get a numpy vector of variants.
    def get_genotypes(self, variant_name):
        """Get a vector of encoded genotypes for the variant.

        This is the core functionality of the Genotype Databases. It should
        be as fast as possible as it will be called repeatedly by the
        tasks. If the structure is in memory, using a hashmap or a pandas
        DataFrame is recommended. If the underlying structure is on disk,
        this should use very good indexing and potentially caching.

        """
        raise NotImplementedError()

    # Experiment initalization including fillin up the database.
    def experiment_init(self, experiment):
        """Experiment specific initialization.

        This method has two main roles. Building a database of
        :py:class:`Variant` objects and doing the db-level filtering of the
        variants. It should also take care of loading the file in memory or of
        indexing if needed.

        """
        # Create the tables corresponding to the SQLAlchemyBase subclasses.
        SQLAlchemyBase.metadata.create_all(experiment.engine)

    # Filtering methods.
    def extract_variants(self, variant_list):
        raise NotImplementedError()

    def filter_maf(self, maf):
        raise NotImplementedError()

    def filter_completion(self, rate):
        raise NotImplementedError()

    # Context manager interface.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class MemoryImpute2Geno(GenotypeDatabaseInterface):
    def __init__(self, filename, samples, filter_probability=0, **kwargs):
        self.filename = filename
        self.load_samples(samples)

        self.impute2file = Impute2File(filename, "dosage",
                                       prob_threshold=filter_probability)

        # Filters (init).
        self.thresh_completion = 0
        self.thresh_maf = 0
        self.names = set()
        self.samples_mask = None

        # The initial filtering is done when the file is parsed. We won't allow
        # the user to apply the filtering methods again.
        self._frozen = False

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

    def experiment_init(self, experiment):
        """Experiment specific initialization.

        This takes care of initializing the database and filtering variants.

        """

        # Call the parent constructor (this will create the db).
        super(MemoryImpute2Geno, self).experiment_init(experiment)

        names = []  # Used to set the index.
        self._mat = []  # The actual dosage vectors.

        db_buffer = []  # List of dicts to bulk insert in the database.
        num_inserts = 0
        con = experiment.engine.connect()  # We also get a connection object.

        for dosage, info in self.impute2file:

            name = info["name"]
            maf = info["maf"]

            # Go through the filters.
            # Name
            if self.names and name not in self.names:
                continue

            # MAF
            if maf < self.thresh_maf:
                continue

            # Completion
            n_missing = np.sum(~np.isnan(dosage))
            n_non_missing = dosage.shape[0] - n_missing

            if self.thresh_completion != 0:
                completion = np.sum(~np.isnan(dosage)) / dosage.shape[0]
                if completion < self.thresh_completion:
                    continue

            # Remove samples if needed.
            if self.samples_mask is not None:
                dosage = dosage[self.samples_mask]

            # Note that probability is already filtered by gepyto.

            # Add to the matrix.
            names.append(name)
            self._mat.append(dosage)

            # Add the variant information to the database.
            db_buffer.append(
                dict(name=name, chrom=info["chrom"], pos=info["pos"],
                     mac=info["minor_allele_count"], n_missing=n_missing,
                     n_non_missing=n_non_missing)
            )

            # We use sqlalchemy core to insert faster.
            # When we have more than 100,000 variants, we bulk insert them.
            if len(db_buffer) >= 100000:
                con.execute(Variant.__table__.insert(), db_buffer)
                num_inserts += len(db_buffer)
                db_buffer = []

        # Bulk insert the remainder.
        if db_buffer:
            con.execute(Variant.__table__.insert(), db_buffer)
            num_inserts += len(db_buffer)
            del db_buffer

        logger.info("Build the variant database ({} entries).".format(
            num_inserts
        ))

        # Set the names as the index for the variant dataframe.
        self._mat = pd.DataFrame(self._mat)
        self._mat.index = names

        # Close the connection.
        con.close()

        # Freeze the database.
        self._frozen = True

    def filter_completion(self, rate):
        if self._frozen:
            raise FrozenDatabaseError()

        logger.info("Setting the completion threshold to {}".format(rate))
        self.thresh_completion = rate

    def filter_maf(self, maf):
        if self._frozen:
            raise FrozenDatabaseError()

        logger.info("Setting the MAF threshold to {}".format(maf))
        self.thresh_maf = maf

    def filter_name(self, names_list):
        # TODO. By modifying gepyto, we could to better filtering on variant
        # names. We would simply not compute the dosage vector for variants
        # we want to ignore.
        if self._frozen:
            raise FrozenDatabaseError()

        logger.info("Keeping only variants with IDs in file: '{}'".format(
            names_list
        ))
        with open(names_list, "r") as f:
            self.names = set([i.rstrip() for i in f.readlines()])

    def exclude_samples(self, samples_list):
        if self._frozen:
            raise FrozenDatabaseError()

        # Build a mask.
        self.samples_mask = np.ones(len(self.samples), dtype=bool)

        # Find the index of the samples to mask.
        for i in samples_list:
            try:
                idx = np.where(self.samples == i)[0]
            except ValueError as e:
                logger.critical("Can't remove samples that are not in the "
                                "genotype database ('{}')".format(i))
                raise e

            if idx.shape[0] > 1:
                raise ValueError("Samples are not unique ('{}').".format(i))

            idx = idx[0]

            self.samples_mask[idx] = False

        # Also remove from the list of samples.
        self.samples = self.samples[self.samples_mask]
