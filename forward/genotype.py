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

import os
import logging
logger = logging.getLogger(__name__)

from gepyto.formats.impute2 import Impute2File
import numpy as np
import pandas as pd
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.ext.hybrid import hybrid_property

from . import SQLAlchemyBase
from .utils import abstract, dispatch_methods, expand

try:  # pragma: no cover
    import pyplink
    HAS_PYPLINK = True
except ImportError:
    HAS_PYPLINK = False


__all__ = ["MemoryImpute2Geno", "PlinkGenotypeDatabase"]


class FrozenDatabaseError(Exception):
    def __str__(self):
        return ("Once initialized, genotype databases are immutable. Further "
                "filtering needs to be done at the Task level.")


class Variant(SQLAlchemyBase):
    """ORM Variant object.

    +----------------+------------------------------------------+------------+
    | Column         | Description                              | Type       |
    +================+==========================================+============+
    | name           | The variant's name (`e.g.` rs12356)      | String(25) |
    +----------------+------------------------------------------+------------+
    | chrom          | The chromosome (`e.g.` '3' or 'X')       | String(15) |
    +----------------+------------------------------------------+------------+
    | pos            | The variant's position on the chromosome | Integer    |
    +----------------+------------------------------------------+------------+
    | mac            | Minor allele count (`e.g.` 125)          | Integer    |
    +----------------+------------------------------------------+------------+
    | minor          | Least common allele (`e.g.` 'T')         | String(10) |
    +----------------+------------------------------------------+------------+
    | major          | Most common allele (`e.g.` 'C')          | String(10) |
    +----------------+------------------------------------------+------------+
    | n_missing      | Number of missing genotypes for this     | Integer    |
    |                | variant                                  |            |
    +----------------+------------------------------------------+------------+
    | n_non_missing  | Number of non-missing genotypes for this | Integer    |
    |                | variant                                  |            |
    +----------------+------------------------------------------+------------+

    Computed fields:

        - ``maf``: mac / (2 :math:`\cdot` n non missing)
        - ``completion_rate``: n non missing / (n non missing + n missing)

    """

    __tablename__ = "variants"

    name = Column(String(25), primary_key=True)
    chrom = Column(String(15))
    pos = Column(Integer)
    mac = Column(Float)  # Minor allele count can be approximated using dosage.
    minor = Column(String(10))
    major = Column(String(10))
    n_missing = Column(Integer)
    n_non_missing = Column(Integer)

    # The maf = mac / (2 * n_non_missing)
    @hybrid_property
    def maf(self):
        return self.mac / (2 * self.n_non_missing)

    # The completion rate = n_non_missing / (n_non_missing + n_missing)
    @hybrid_property
    def completion_rate(self):
        return self.n_non_missing / (self.n_non_missing + self.n_missing)


@abstract
class AbstractGenotypeDatabase(object):
    """Abstract genotype container.

    This class defines the standardized methods to organize the genotype access
    procedures used by Forward.

    """
    def __init__(self, **kwargs):
        dispatch_methods(self, kwargs)

    # Sample management interface.
    def get_sample_order(self):
        """Return a list of the (ordered) samples as represented in the
           database.

        The experiment will pass the results of this method to the phenotype
        container's ``set_sample_order`` method.

        """
        return self.samples

    def query_variants(self, session, fields=None):
        """Return a query object for variants.

        :param session: A session object to interface with the Variant table.
        :type session: :py:class:`sqlalchemy.orm.session.Session`

        :param fields: A list of attributes to query. They should correspond
                       to columns of the :py:class:`Variant` table.
        :type fields: list

        If fields are given, they are queried. Alternatively a query for the
        Variant objects is returned.

        Variant data is stored in a SQLAlchemy database. This method provides
        a shortcut to query it in a more pythonic way.

        """
        if fields:
            args = []
            if not type(fields) in (tuple, list):
                fields = [fields]

            for field in fields:
                if hasattr(Variant, field):
                    args.append(getattr(Variant, field))
                else:
                    raise ValueError(
                        "No column {} for Variants.".format(field)
                    )

            return session.query(*args)

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

    # Experiment initalization including filling up the database and filtering
    # variants.
    def experiment_init(self, experiment):
        """Experiment specific initialization.

        This method has two main roles. Building a database of
        :py:class:`Variant` objects and doing the db-level filtering of the
        variants. It should also take care of loading the file in memory or of
        indexing if needed.

        """
        # Create the tables corresponding to the SQLAlchemyBase subclasses.
        Variant.__table__.create(experiment.engine, checkfirst=True)

    # Filtering methods.
    def filter_name(self, variant_list):
        """Filtering by variant id.

        The argument can be either a path to a file or a list of names.
        """
        raise NotImplementedError()

    def filter_maf(self, maf):
        raise NotImplementedError()

    def filter_completion(self, rate):
        raise NotImplementedError()

    # Static utilities.
    @staticmethod
    def load_samples(filename):
        """Read a list of samples from a single column file."""
        logger.info("Loading samples from {}".format(filename))
        with open(filename, "r") as f:
            samples = [i.rstrip() for i in f]

        return np.array(samples, dtype=str)


class MemoryImpute2Geno(AbstractGenotypeDatabase):
    """Container for small(ish) IMPUTE2 files.

    :param filename: The filename for the IMPUTE2 file.
    :type filename: str

    :param samples: A list containing a single column and no header. The rows
                    are the ordered sample IDs.
    :type sample: str

    :param filter_probability: A cutoff for imputation probability. Only
                               genotypes with an imputation probability above
                               this threshold will be used for the analysis.
    :type filter_probability: float

    .. warning::
        This implementation load the whole file in memory (hence the name).
        Be careful and make sure that you have enough RAM to hold everything.

        It would be fairly easy to subclass this and support lazily reading
        genotype data from the disk. Feel free to contribute this feature if
        you need it.

    """
    def __init__(self, filename, samples, filter_probability=0, **kwargs):
        self.filename = expand(filename)
        self.samples = self.load_samples(expand(samples))

        self.impute2file = Impute2File(self.filename, "dosage",
                                       prob_threshold=filter_probability)

        # Filters (init).
        self.thresh_completion = 0
        self.thresh_maf = 0
        self.names = set()
        self.samples_mask = None

        # The initial filtering is done when the file is parsed. We won't allow
        # the user to apply the filtering methods again.
        self._frozen = False

        super(MemoryImpute2Geno, self).__init__(**kwargs)

    def experiment_init(self, experiment, batch_insert_n=100000):
        """Experiment specific initialization.

        This takes care of initializing the database and filtering variants. It
        is automatically called by the Experiment.

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

            # Go through the filters.
            # Name
            if self.names and name not in self.names:
                continue

            # Completion
            n_missing = np.sum(np.isnan(dosage))
            n_non_missing = dosage.shape[0] - n_missing

            if self.thresh_completion != 0:
                completion = n_non_missing / dosage.shape[0]
                if completion < self.thresh_completion:
                    continue

            # MAF
            if info["maf"] < self.thresh_maf:
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
                dict(name=name, chrom=info["chrom"], pos=int(info["pos"]),
                     mac=float(info["minor_allele_count"]),
                     minor=info["minor"], major=info["major"],
                     n_missing=int(n_missing),
                     n_non_missing=int(n_non_missing))
            )

            # We use sqlalchemy core to insert faster.
            # When we have more than 100,000 variants, we bulk insert them.
            if len(db_buffer) >= batch_insert_n:
                con.execute(Variant.__table__.insert(), db_buffer)
                num_inserts += len(db_buffer)
                db_buffer = []

        # Bulk insert the remainder.
        if db_buffer:
            con.execute(Variant.__table__.insert(), db_buffer)
            num_inserts += len(db_buffer)
            del db_buffer

        logger.info("Built the variant database ({} entries).".format(
            num_inserts
        ))

        # Set the names as the index for the variant dataframe.
        self._mat = pd.DataFrame(self._mat)
        self._mat.index = names

        # Close the connection.
        con.close()

        # Freeze the database.
        self._frozen = True

    def get_genotypes(self, variant_name):
        """Get a vector of genotypes for a variant.

        :param variant_name: The variant name (e.g. rs123456)
        :type variant_name: str

        :returns: A vector of genotypes (g = 0, 1 or 2; the number of
                  non-reference alleles).
        :rtype: np.nadarray

        """
        # We want to be able to get genotypes even before experiment
        # initialization, mainly for testing. To support this, we will look for
        # the variant in the impute2 file and reset the file.
        if not hasattr(self, "_mat"):  # Check if it was init.
            logger.warning("This should only be logged during testing. If you "
                           "see this during normal execution, please report "
                           "it on Github.")
            # Try to find the variant in the impute2file.
            self._mat, info = self.impute2file.as_matrix()
            self._mat = pd.DataFrame(self._mat.T)
            self._mat.index = info["name"]

        try:
            vect = self._mat.loc[variant_name, :].values
            return vect
        except KeyError:
            msg = "Variant {} not found in genotype database.".format(
                variant_name
            )
            raise ValueError(msg)

    def filter_completion(self, rate):
        """Apply a filter on completion rate.

        :param rate: The minimum completion rate for inclusion.
        :type rate: float

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()

        logger.info("Setting the completion threshold to {}".format(rate))
        self.thresh_completion = rate

    def filter_maf(self, maf):
        """Apply a filter on minor allele frequency.

        :param rate: The minimum maf for inclusion.
        :type rate: float

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()

        logger.info("Setting the MAF threshold to {}".format(maf))
        self.thresh_maf = maf

    def filter_name(self, names_list):
        """Only includes variants in a list.

        :param names_list: Either a list of variant names or the path to a file
                           containing a single column of variant names.
        :type names_list: str

        This is a configuration option.

        """
        # TODO. By modifying gepyto, we could to better filtering on variant
        # names. We would simply not compute the dosage vector for variants
        # we want to ignore.
        if self._frozen:
            raise FrozenDatabaseError()

        # A list of IDs.
        if type(names_list) in (list, tuple):
            self.names = names_list

        # A file of IDs.
        else:
            logger.info("Keeping only variants with IDs in file: '{}'".format(
                names_list
            ))
            if not os.path.isfile(names_list):
                names_list = expand(names_list)

            with open(names_list, "r") as f:
                self.names = set(f.read().splitlines())

    def exclude_samples(self, samples_list):
        """Exclude samples in the list.

        :param samples_list: A list of samples to exclude.
        :type samples_list: list

        The returned genotype vectors will not have genotypes for excluded
        samples (i.e. they will be n elements shorter, n = len(samples_list))

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()

        # Build a mask.
        self.samples_mask = np.ones(len(self.samples), dtype=bool)

        # Find the index of the samples to mask.
        for i in samples_list:
            idx = np.where(self.samples == i)[0]
            if len(idx) == 0:
                raise ValueError("Can't remove samples that are not in the "
                                 "genotype database ('{}')".format(i))

            if idx.shape[0] > 1:
                raise ValueError("Samples are not unique ('{}').".format(i))

            idx = idx[0]

            self.samples_mask[idx] = False

        # Also remove from the list of samples.
        self.samples = self.samples[self.samples_mask]

    def close(self):
        self.impute2file.close()


class PlinkGenotypeDatabase(AbstractGenotypeDatabase):
    """Container for binary PLINK files.

    :param prefix: The prefix of the PLINK bed, bim, fam files.
    :type prefix: str

    This container relies on `pyplink <http://github.org/lemieuxl/pyplink>`_.

    """
    def __init__(self, prefix, **kwargs):
        if not HAS_PYPLINK:
            raise Exception("Install pyplink to use the '{}' class.".format(
                self.__class__.__name__,
            ))

        self.ped = pyplink.PyPlink(expand(prefix))
        self.fam = self.ped.get_fam()
        self.bim = self.ped.get_bim()

        # Filters.
        self.min_maf = 0
        self.min_completion = 0
        self.good_names = []
        self._frozen = False

        super(PlinkGenotypeDatabase, self).__init__(**kwargs)

    def get_sample_order(self):
        """Return a list of the (ordered) samples as represented in the
           database.

        """
        return list(self.fam["iid"].values)

    def get_genotypes(self, variant_name):
        """Returns a genotype vector for the given variant."""
        return self.ped.get_geno_marker(variant_name)

    def experiment_init(self, experiment):
        """Initialization method called by the Experiment.

        Applies filtering, creates and fills the database.

        """
        # Create the table.
        super(PlinkGenotypeDatabase, self).experiment_init(experiment)

        # Filter and fill the database.
        con = experiment.engine.connect()
        db_variants = []
        for name, geno in self.ped:
            info = self.bim.loc[name, :]

            # Name filtering.
            if self.good_names:
                if name not in self.good_names:
                    continue

            # maf filtering.
            mac = np.nansum(geno)
            maf = mac / (2 * geno.shape[0])
            if maf < self.min_maf:
                continue

            # completion filtering.
            n_missing = np.sum(np.isnan(geno))
            n_non_missing = np.sum(~np.isnan(geno))

            completion = n_non_missing / geno.shape[0]
            if completion < self.min_completion:
                continue

            # Everything passed, we can add to the db.
            db_variants.append(
                dict(name=name, chrom=info.chrom, pos=int(info.pos),
                     mac=float(mac), n_missing=int(n_missing),
                     n_non_missing=int(n_non_missing),
                     minor=info["a1"], major=info["a2"])
            )

        con.execute(Variant.__table__.insert(), db_variants)
        logger.info("Built the variant database ({} entries).".format(
            len(db_variants)
        ))
        self._frozen = True

    # Filtering methods.
    def filter_name(self, variant_list):
        """Filter by variant name.

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()

        if type(variant_list) in (tuple, list):
            self.good_names = variant_list
        else:
            with open(variant_list, "r") as f:
                self.good_names = f.read().split()

    def filter_maf(self, maf):
        """Filters variants by allele frequency (MAF).

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()
        self.min_maf = maf

    def filter_completion(self, rate):
        """Filters variants by completion rate (rate of no-calls).

        This is a configuration option.

        """
        if self._frozen:
            raise FrozenDatabaseError()
        self.min_rate = rate
