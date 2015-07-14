# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is used to create reports from forward experiments.

"""

from __future__ import division

import shutil
from pkg_resources import resource_filename
import collections
import os
import datetime
import webbrowser
import logging
logger = logging.getLogger()

import sqlalchemy

import scipy.stats
import matplotlib
import matplotlib.cm
import numpy as np

from six.moves import cPickle as pickle
from jinja2 import Environment, PackageLoader

from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models import HoverTool

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


class NoHandlerException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class Report(object):
    """Class used to create reports.

    It can be initialized from an Experiment object or from a path to the
    sqlite3 database that contains experimental results.

    """

    def __init__(self, experiment):

        if type(experiment) is Experiment:
            self.experiment = experiment.info
        else:
            # Assume this is the name of the Experiment.
            info_pkl = os.path.join(experiment, "experiment_info.pkl")
            with open(info_pkl, "rb") as f:
                self.experiment = pickle.load(f)

        logger.info("Generating a report for experiment {}".format(
            self.experiment["name"]
        ))

        # SQLAlchemy
        self.engine = sqlalchemy.create_engine(self.experiment["engine_url"])
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        # Create a report folder.
        self.report_path = os.path.join(self.experiment["name"], "report")

        # Create an assets folder (and the parents).
        self.assets = os.path.join(self.report_path, "assets")
        deepest = os.path.join(self.assets, "images")
        if not os.path.isdir(deepest):
            os.makedirs(deepest)

        # jinja2
        self.env = Environment(loader=PackageLoader("forward", "templates"))
        self.env.globals = {"assets": "assets"}  # Relative url
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
            try:
                section = handlers[task_type](task, self)
            except KeyError:
                raise NoHandlerException("Could not find a report handler "
                                         "for the '{}'.".format(task_type))

            self.sections.append(section)

    def query(self, *args, **kwargs):
        return self.session.query(*args, **kwargs)

    def html(self):
        """Generate and open the html report."""
        # Add datetime.
        self.contents["now"] = datetime.datetime.now()

        fn = os.path.join(self.report_path, "report.html")
        with open(fn, "wb") as f:
            f.write(
                self.template.render(
                    sections=self.sections, **self.contents
                ).encode("utf-8")
            )

        # We need to copy the template dependencie (e.g. css files).
        try:
            os.makedirs(os.path.join(self.report_path, "css"))
        except OSError:
            pass  # The directory probably already exists.

        shutil.copyfile(
            resource_filename(__name__, "templates/css/default.css"),
            os.path.join(self.report_path, "css", "default.css")
        )

        webbrowser.open_new_tab("file://{}".format(os.path.abspath(fn)))


class Section(object):
    def __init__(self, task_id, report):
        self.task_id = task_id
        self.report = report

        # Load the task specific meta information if it exists.
        path = os.path.join(self.report.experiment["name"], "tasks",
                            self.task_id, "task_info.pkl")
        if os.path.isfile(path):
            with open(path, "rb") as f:
                self.info = pickle.load(f)
        else:
            self.info = {}

    def html(self):
        raise NotImplementedError


@register_handler("LogisticTest")
class LogisticReportSection(Section):
    def __init__(self, task_id, report):
        super(LogisticReportSection, self).__init__(task_id, report)
        self.template_vars = {
            "variables": self._get_variables(),
            "corrplot": self._create_variables_corrplot(),
            "num_variants": self._number_analyzed_variants(),
            "qq_plot": self._qq_plot(),
            "results": self._parse_results(),
            "task_info": self.info,
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

        names = self.report.experiment["outcomes"]

        title = "Corrleation matrix heatmap for the analyzed variables."
        p = figure(title=title, x_range=names, y_range=names[::-1],
                   plot_width=500, plot_height=500,
                   tools="resize,hover,save,reset", title_text_font_size="8pt")

        colors = matplotlib.cm.coolwarm(np.linspace(0, 1, 100))
        colors = [tu for tu in (255 * colors[:, :3])]
        for i in range(len(colors)):
            html = "#{}{}{}".format(
                *[hex(int(j)).ljust(4, "0")[2:] for j in colors[i]]
            )
            colors[i] = html

        xs = []
        ys = []
        values = []
        mapped_colors = []

        for x in range(len(names)):
            for y in range(len(names) - x):
                xs.append(names[x])
                ys.append(names[corr_mat.shape[0] - y - 1])
                val = corr_mat[x, corr_mat.shape[0] - y - 1]
                values.append("{:.3f}".format(val))

                color = int(
                    round(0.5 * (len(colors) - 1) * val +
                          (len(colors) - 1) / 2)
                )
                mapped_colors.append(colors[color])

        source = ColumnDataSource(
            data=dict(x=xs, y=ys, color=mapped_colors, value=values)
        )

        p.rect("x", "y", 0.95, 0.95, color="color", source=source)

        p.grid.grid_line_color = None
        p.xaxis.major_label_orientation = np.pi / 3
        for axis in p.axis:
            axis.major_label_text_font_size = "7pt"

        hover = p.select({"type": HoverTool})
        hover.tooltips = """
            <div class="tooltip">
              <p><strong>Variables:</strong> @x - @y</p>
              <p><strong>Correlation:</strong> @value</p>
            </div>
        """

        return components(p)

    def _number_analyzed_variants(self):
        """Find the number of analyzed variants in the database."""
        return self.report.query(ExperimentResult.entity_name).\
                           filter_by(task_name=self.task_id).\
                           distinct().count()

    def _qq_plot(self):
        """A colored QQ plot showing the results per phenotype."""
        query = self.report.query(ExperimentResult.phenotype,
                                  ExperimentResult.significance).\
                            filter_by(task_name=self.task_id)

        results = sorted(query.all(), key=lambda x: x[1])
        p_values = np.array([i[1] for i in results])
        p_values = -1 * np.log10(p_values)
        n = len(p_values)

        expected = -1 * np.log10(np.arange(1, n + 1))

        # Computing the 95% CI
        c975 = np.zeros(n)
        c025 = np.zeros(n)

        for i in range(1, n + 1):
            c975[i - 1] = scipy.stats.beta.ppf(0.975, i, n - i + 1)
            c025[i - 1] = scipy.stats.beta.ppf(0.025, i, n - i + 1)

        c975 = -1 * np.log10(c975)
        c025 = -1 * np.log10(c025)

        # Plotting
        title = "QQ Plot of the association results"
        p = figure(title=title, plot_width=650, plot_height=480,
                   tools="save,reset", title_text_font_size="8pt")

        p.patches(
            [np.hstack((expected, expected[::-1]))],
            [np.hstack((c025, c975[::-1]))],
            color="#dddddd",
            fill_alpha=0.9
        )

        p.circle(expected, p_values, size=1)

        p.grid.grid_line_color = None
        p.xaxis.axis_label = "-log(expected)"
        p.yaxis.axis_label = "-log(observed)"
        for axis in p.axis:
            axis.axis_label_text_font_size = "7pt"

        return components(p)

    def _parse_results(self):
        """Fetch analysis results in the database and format them. """
        query = self.report.query(ExperimentResult).\
                            filter_by(task_name=self.task_id).\
                            filter(ExperimentResult.significance < 0.05).\
                            order_by(ExperimentResult.significance.asc())

        results = []  # List of Result named tuples.
        result = collections.namedtuple(
            "Result",
            ("variant", "phenotype", "p", "low", "odds_ratio", "high")
        )

        for res in query:
            results.append(result(
                res.entity_name,
                res.phenotype,
                "{:.3e}".format(res.significance),
                "{:.3f}".format(np.exp(res.confidence_interval_min)),
                "{:.3f}".format(np.exp(res.coefficient)),
                "{:.3f}".format(np.exp(res.confidence_interval_max)),
            ))

        return results

    def html(self):
        template = self.report.env.get_template("section_logistic.html")
        return template.render(**self.template_vars)

@register_handler("LinearRegressionTest")
class LinearReportSection(Section):
    def __init__(self, task_id, report):
            super(LinearReportSection, self).__init__(task_id, report)
            self.template_vars = {}

    def html(self):
            template = self.report.env.get_template("section_linear.html")
            return template.render(**self.template_vars)
