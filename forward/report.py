# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is used to create reports from forward experiments.

"""

try:
    import cPickle as pickle
except ImportError:
    import pickle  # Py3

import os
import datetime
import webbrowser
import logging

logger = logging.getLogger()

import sqlalchemy

import scipy.stats
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sbn

from jinja2 import Environment, PackageLoader

from . import SQLAlchemySession
from .experiment import ExperimentResult, Experiment
from .phenotype.variables import Variable


handlers = {}

def register_handler(binding):
    def decorator(handler):
        global handlers
        handlers[binding] = handler
        return handler
    return decorator


class Report(object):
    """Class used to create reports.

    It can be initialized from an Experiment object or from a path to the
    sqlite3 database that contains experimental results.

    """

    def __init__(self, experiment):

        if type(experiment) is Experiment:
            experiment = experiment.info
        else:
            # Assume this is the name of the Experiment.
            info_pkl = os.path.join(experiment, "experiment_info.pkl")
            with open(info_pkl, "rb") as f:
                experiment = pickle.load(f)

        self.experiment = experiment
        logger.info("Generating a report for experiment {}".format(
            experiment["name"]
        ))

        # SQLAlchemy
        self.engine = sqlalchemy.create_engine(experiment["engine_url"])
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        # Create an assets folder.
        self.assets = "assets"
        if not os.path.isdir(self.assets):
            os.makedirs(os.path.join(self.assets, "images"))

        # jinja2
        self.env = Environment(loader=PackageLoader("forward", "templates"))
        self.env.globals = {"assets": self.assets}
        self.template = self.env.get_template("default.html")

        self.contents = {}
        self.sections = []
        self._dispatch_sections()

    def _dispatch_sections(self):
        """For every task, dispatch to a section manager that will understand.

        """
        # Get a list of tasks.
        for task in self.query(ExperimentResult.task_name).distinct():
            task = task[0]
            task_type = task.split("_")[1]
            self.sections.append(handlers[task_type](task, self))

    def query(self, *args, **kwargs):
        return self.session.query(*args, **kwargs)

    def html(self):
        """Generate and open the html report."""
        # Add datetime.
        self.contents["now"] = datetime.datetime.now()

        fn = "test.html"
        with open(fn, "wb") as f:
            f.write(
                self.template.render(
                    sections=self.sections, **self.contents
                ).encode("utf-8")
            )
        webbrowser.open_new_tab("file://{}".format(os.path.abspath(fn)))


class Section(object):
    def __init__(self, task_id, report):
        self.task_id = task_id
        self.report = report

    def html(self):
        raise NotImplementedError


@register_handler("GLMTest")
class GLMReportSection(Section):
    def __init__(self, task_id, report):
        super(GLMReportSection, self).__init__(task_id, report)
        self.template_vars = {
            "variables": self._get_variables(),
            "corrplot": self._create_variables_corrplot(),
            "num_variants": self._number_analyzed_variants(),
            "qq_plot": self._qq_plot(),
        }

    def _get_variables(self):
        # Get variable names for this task.
        variables = []
        for var_name in self.report.query(ExperimentResult.phenotype).\
                                    filter_by(task_name=self.task_id).\
                                    distinct():
            # TODO: Refactor ExperimentResult so that .phenotype is a FK to
            # Variable objects. Then we can use a join here instead of two
            # queries. Performance impact should be minimal though...

            # Get the corresponding variable.
            variables.append(
                self.report.query(Variable).filter_by(name=var_name[0]).one()
            )

        return variables

    def _create_variables_corrplot(self):
        """Create a correlation matrix showing off variable correlation."""

        corr_mat_fn = self.report.experiment.get("phen_correlation")
        if corr_mat_fn is None:
            return None

        corr_mat = np.load(corr_mat_fn)

        fig = plt.figure(figsize=(9, 8), tight_layout=True)
        sbn.symmatplot(corr_mat, names=self.report.experiment["outcomes"],
                       cmap="coolwarm")

        path = os.path.join(self.report.assets, "images")

        plt.savefig(os.path.join(path, "corrplot.png"))
        plt.close()

        return os.path.join("images", "corrplot.png")

    def _number_analyzed_variants(self):
        """Find the number of analyzed variants in the database."""
        return self.report.query(ExperimentResult.entity_name).\
                           filter_by(task_name=self.task_id).\
                           distinct().count()

    def _qq_plot(self):
        """A colored QQ plot showing the results per phenotype."""
        code = 0
        phen_codes = {}
        data = []

        query = self.report.query(ExperimentResult.phenotype,
                                  ExperimentResult.significance).\
                            filter_by(task_name=self.task_id)

        for phen, p in query:
            if phen not in phen_codes:
                phen_codes[phen] = code
                code += 1
            data.append((phen_codes[phen], p))

        data = np.array(data)

        fig, ax = plt.subplots(1, 1)

        quantiles, fit = scipy.stats.probplot(data[:, 1], dist="norm")
        osm, osr = quantiles
        slope, intercept, r = fit

        colors = ["#F44336", "#9C27B0", "#03A9F4", "#009688", "#4CAF50",
                  "#CDDC39", "#FFEB3B", "#FF9800", "#FF5722"]

        # Plot per phenotype.
        deviations = ((slope * osm + intercept) - osr) ** 2
        for i in range(code):
            mask = data[:, 0] == i
            # TODO Use a better threshold for coloring.
            dev_mask = (deviations > 0.02) & mask
            non_dev_mask = (deviations <= 0.02) & mask

            # Plot black for non-deviating.
            ax.scatter(osm[non_dev_mask], osr[non_dev_mask], color="black",
                       s=10, marker="o")

            # Plot colored dots (deviating).
            phen = [(k, v) for k, v in phen_codes.items() if v == i][0][0]
            ax.scatter(osm[dev_mask], osr[dev_mask], color=colors[i], s=10,
                       marker="o", label=phen)

        xs = np.arange(*ax.get_xlim())
        ax.plot(xs, slope * xs + intercept, "--", color="#6D784B",
                label="$R^2 = {:.4f}$".format(r))
        ax.legend(loc="lower right")

        ax.set_xlabel("Quantile")
        ax.set_ylabel("Ordered Values")

        path = os.path.join(self.report.assets, "images", "qqplot.png")
        plt.savefig(path)
        plt.close()

        return os.path.join("images", "qqplot.png")


    def html(self):
        template = self.report.env.get_template("section_glm.html")
        return template.render(**self.template_vars)
