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

        # SQLAlchemy
        self.engine = sqlalchemy.create_engine(experiment["engine_url"])
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        # jinja2
        self.env = Environment(loader=PackageLoader("forward", "templates"))
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
                self.template.render(sections=self.sections, **self.contents)
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

    def html(self):
        template = self.report.env.get_template("section_glm.html")
        return template.render(**self.template_vars)
