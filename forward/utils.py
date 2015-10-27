# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is for short utility functions.

"""


import collections
import uuid
import os
import multiprocessing
import json

from six.moves import range
from gepyto.formats.gtf import GTFFile


class AbstractClassException(Exception):
    def __str__(self):
        return "Can't initialize an abstract class."


def namedtuple_to_dict(tu):
    """Convert a namedtuple to a regular Python dict."""
    return {k: getattr(tu, k) for k in tu._fields}


def expand(s):
    """Expand environment variables and the tilde."""
    return os.path.expandvars(os.path.expanduser(s))


def format_time_delta(delta):
    """Format a timedelta object into a human readable representation."""

    s = delta.seconds
    hours = s // 3600
    s -= hours * 3600
    minutes = s // 60
    s -= minutes * 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, s)


def abstract(cls):
    """Decorator to be used to mark abstract classes.

    This is used because sometimes it is useful to have a parent class that
    is initializable (that does not raise NotImplementedError) but that you
    don't want to actually be used (even though it would not procude
    immediate exceptions. For this reason, you can decorate such classes with
    the @abstract decorator.

    This will make it possible for subclasses to call any parent function
    (_e.g._ the __init__ function) while making sure that the parent never
    get initialized.

    """
    init = cls.__init__

    def safe_init(self, *args, **kwargs):
        if self.__class__ is cls:
            raise AbstractClassException()
        return init(self, *args, **kwargs)

    cls.__init__ = safe_init
    return cls


def dispatch_methods(self, kwargs):
    """Call methods with the parameters as specified in kwargs.

    This assumes that self is an instance of an unknown object and that kwargs
    is an arbitrary dictionary.

    """
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
        raise ValueError(message)


def check_rpy2():
    """Check if rpy2 is currently installed."""
    try:
        import rpy2
        return True
    except ImportError:
        return False


def Parallel(num_cpu, f):
    if num_cpu == 1:
        return SingleCoreWorkQueue(f)
    elif num_cpu > 1:
        return MultiprocessingQueue(num_cpu, f)
    else:
        raise ValueError("Invalid number of CPUs to use ({}).".format(num_cpu))


class SingleCoreWorkQueue(object):
    """Emulates the Parallel interface without using multiple CPUs.

    :param f: The target function.
    :type f: function

    See :py:class:`Parallel` for more details.

    """
    def __init__(self, f):
        self.f = f
        self.results = []

    def push_work(self, tu):
        self.results.append(self.f(*tu))

    def get_result(self):
        if self.results:
            return self.results.pop()

    def done_pushing(self):
        pass


class MultiprocessingQueue(object):
    """Class used to parallelize computation.

    :param num_cpu: Number of CPUs to use (size of the worker pool).
    :type num_cpu: int

    :param f: The target function.
    :type f: function

    """
    def __init__(self, num_cpu, f):
        self.num_cpu = num_cpu
        self.f = f

        self.job_queue = multiprocessing.Queue()
        self.results_queue = multiprocessing.Queue()

        self.pool = []
        for cpu in range(self.num_cpu):
            p = multiprocessing.Process(
                target=self._process,
            )
            p.start()
            self.pool.append(p)

    def push_work(self, tu):
        """Add work to the queue."""
        if type(tu) is not tuple:
            raise TypeError("push_work takes a tuple of arguments for the "
                            "function (f).")
        self.job_queue.put(tu)

    def get_result(self):
        """Fetches results from the result queue."""
        if self.job_queue.empty() and self.results_queue.empty():
            # Check if the processees are done.
            if all([not p.is_alive for p in self.pool]):
                self.results_queue.close()
                return

        return self.results_queue.get()

    def done_pushing(self):
        """Signals that we will not be pushing more work."""
        self.job_queue.put(None)

    def _process(self):
        while True:
            data = self.job_queue.get()

            if data is None:
                self.job_queue.put(data)  # Put the sentinel back.
                break

            results = self.f(*data)

            self.results_queue.put(results)


class EnsemblAnnotationParser(object):
    """Parser for GTF/GFF files from Ensembl (used to rebuild hierarchy).

    This is used because we want to show some hierarchy in the annotation. We
    want gene -> transcript -> exon.

    """
    def __init__(self, filename):
        self.genes = {}
        with GTFFile(filename) as gtf:
            # We need to build the hierarchy in order.
            _build_queue = collections.defaultdict(list)
            for annot in gtf:
                if annot.features == "gene":
                    self._add_gene(annot)
                elif annot.features == "transcript":
                    _build_queue[0].append(annot)
                elif annot.features in ("UTR", "exon", "CDS"):
                    _build_queue[1].append(annot)

        for annot in _build_queue[0]:
            self._add_transcript(annot)

        for annot in _build_queue[1]:
            self._add_transcript_feature(annot)

    def _add_gene(self, annot):
        """Add a gene node to the graph.

        This method can be called with a GTF line object or with a string
        containing the gene name. This is authorized because the genes are
        top level components so we don't really need the extra information to
        place it in the hierarchy.

        """
        if hasattr(annot, "attributes"):
            name = annot.attributes["gene_id"]
            self.genes[name] = {
                "value": namedtuple_to_dict(annot),
                "transcripts": {}
            }
            return self.genes[name]
        else:
            self.genes[annot] = {"value": None, "transcripts": {}}
            return self.genes[annot]

    def _add_transcript(self, annot):
        gene_name = annot.attributes["gene_id"]
        transcript_name = annot.attributes["transcript_id"]
        parent_gene = self.genes.get(gene_name)

        if parent_gene is None:
            parent_gene = self._add_gene(gene_name)

        transcript = {
            "value": namedtuple_to_dict(annot), "exon": {}, "CDS": {},
            "UTR": {}
        }
        parent_gene["transcripts"][transcript_name] = transcript
        return transcript

    def _add_transcript_feature(self, annot):
        feature_type = annot.features
        transcript_name = annot.attributes["transcript_id"]
        gene_name = annot.attributes["gene_id"]

        try:
            transcript = self.genes[gene_name]["transcripts"][transcript_name]
        except KeyError:
            raise ValueError("Some parents are missing from the GTF File. "
                             "Make sure that all the references are correct.")

        if feature_type == "exon":
            feature_id = annot.attributes["exon_id"]
        else:
            feature_id = self._generate_id()

        # Check for colisions in the generated ids.
        assert transcript[feature_type].get(feature_id) is None
        annot = namedtuple_to_dict(annot)
        transcript[feature_type][feature_id] = annot

        return annot

    def _generate_id(self):
        return str(uuid.uuid4()).split("-")[0]

    def to_json(self):
        return json.dumps(self.genes)
