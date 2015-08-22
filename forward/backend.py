# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is a flask backend providing a REST api to add interactivity
to the report.

The backend needs to be able to restore the phenotype database functionality
and be able to generate plots.

These methods will return json to the report. Alternatively, they will return
the native python objects. This way, the functionality will all be here and
everything that's related to the report's content and formatting will be in the
report module.

"""

from __future__ import division

import json
import os

import scipy.stats
import numpy as np
import h5py
import sqlalchemy
import matplotlib.cm
from six.moves import cPickle as pickle
import pygments
from pygments.lexers import YamlLexer
from pygments.formatters import HtmlFormatter
from flask import (Flask, request, url_for, render_template, jsonify,
                   render_template)
app = Flask(__name__)

from . import genotype, experiment
from . import FORWARD_REPORT_ROOT, STATIC_ROOT, SQLAlchemySession
from .phenotype.variables import Variable, DiscreteVariable, ContinuousVariable
from .phenotype.db import apply_transformation
from .utils import format_time_delta


www_backend = None
BASE = os.path.abspath(os.path.dirname(__file__))


class Backend(object):
    """Class that provides all api functionality to be used for both report
       creation and the rest api.

    """

    def __init__(self, experiment_name):
        self.engine = experiment.Experiment.get_engine(
            experiment_name, "sqlite"
        )
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        self.hdf5_file = h5py.File(
            os.path.join(experiment_name, "phenotypes.hdf5"),
            "r"
        )

        self.config = os.path.join(experiment_name, "configuration.yaml")
        if not os.path.isfile(self.config):
            self.config = None

        # Experiment info.
        filename = os.path.join(experiment_name, "experiment_info.pkl")
        with open(filename, "rb") as f:
            self.info = pickle.load(f)

        # Correlation matrix.
        filename = os.path.join(experiment_name, "phen_correlation_matrix.npy")
        self.correlation_matrix = np.load(filename)

    def get_variants(self, add_maf=False):
        variants = self.session.query(genotype.Variant).all()
        if not add_maf:
            return [v.to_json() for v in variants]

        response = []
        for v in variants:
            d = v.to_json()
            d["maf"] = v.maf
            response.append(d)

        return response

    def get_variables(self, var_type=None, order_by=None, ascending=True):
        if var_type is None:
            variable_class = Variable
        elif var_type == "discrete":
            variable_class = DiscreteVariable
        elif var_type == "continuous":
            variable_class = ContinuousVariable
        else:
            raise ValueError("Unknown variable type '{}'.".format(var_type))

        variables = self.session.query(variable_class)

        if order_by is not None:
            key = getattr(variable_class, order_by)
            if not ascending:
                key = sqlalchemy.desc(key)

            variables = variables.order_by(key)

        return [variable.to_json() for variable in variables.all()]


    def get_outcome_vector(self, variable, transformation=None, nan=True):
        try:
            y = self.hdf5_file[variable]
        except KeyError:
            msg = "Could not find variable {} in serialized file."
            raise ValueError(msg.format(variable))
        if transformation:
            y = apply_transformation(transformation, y)
        if not nan:
            y = y[~np.isnan(y)]

        return y

    def get_variable_histogram(self, variable, transformation=None, **kwargs):
        y = self.get_outcome_vector(variable, transformation, nan=False)
        return np.histogram(y, **kwargs)

    def get_variable_normal_qqplot(self, variable, transformation=None):
        obs = self.get_outcome_vector(variable, transformation, nan=False)
        obs = sorted(obs)

        # Compare to a N(mu, sigma)
        mu = np.mean(obs)
        std = np.std(obs)

        # Generate the expected (we use the offsetting strategy that
        # statsmodels uses).
        a = 0
        n = len(obs)
        exp = scipy.stats.norm.ppf(
            (np.arange(1, n + 1) - a) / (n - 2 * a + 1),
            loc=mu, scale=std
        )

        # Fit a regression line.
        m, b = self._fit_line(obs, exp)

        return exp, obs, m, b

    def get_variable_corrplot(self):
        names = self.info["outcomes"]
        corr_mat = self.correlation_matrix
        return corr_mat, names

    def get_related_phenotypes_exclusions(self):
        exclusions = self.session.query(
            experiment.RelatedPhenotypesExclusions
        )

        counts = {"exclusions": {}}
        counts["threshold"] = self.info.get(
            "phenotype_correlation_for_exclusion"
        )
        for e in exclusions:
            if counts.get(e.phen1) is None:
                counts["exclusions"][e.phen1] = {"related": [],
                                                 "n_excluded": 0}

            counts["exclusions"][e.phen1]["related"].append(e.phen2)
            counts["exclusions"][e.phen1]["n_excluded"] += e.n_excluded

        return counts

    def get_tasks(self):
        tasks = self.session.query(
            experiment.ExperimentResult.task_name
        ).distinct()
        return [tu[0] for tu in tasks]

    def p_value_qq_plot(self, task):
        """Return the scatter data and confidence bands.

        This is assuming we're expecting a uniform distribution. We also take
        a log transform to accentuate small differences.

        """
        # Get the association p values (or other significance metric).
        # expected, observed, ci, phenotype, variant, effect.
        results = self.session.query(experiment.ExperimentResult)\
                    .filter(experiment.ExperimentResult.task_name.like(task))\
                    .order_by(experiment.ExperimentResult.significance)

        n = results.count()
        out = []
        for i, res in enumerate(results):
            ppf = scipy.stats.beta.ppf
            d = {
                "expected": -1 * np.log10((i + 1) / n),
                "observed": -1 * np.log10(res.significance),
                "ci": [
                    -1 * np.log10(ppf(0.975, i + 1, n - i + 2)),
                    -1 * np.log10(ppf(0.025, i + 1, n - i + 2))
                ],
                "phenotype": res.phenotype,
                "variant": res.entity_name,
                "effect": res.coefficient
            }
            out.append(d)

        return out


    def get_results(self, task, filters=[], order_by=None, ascending=True):
        results = self.session.query(experiment.ExperimentResult)\
                    .filter(experiment.ExperimentResult.task_name.like(task))

        if order_by is not None:
            field = getattr(experiment.ExperimentResult, order_by)
            if not ascending:
                field = sqlalchemy.desc(field)

            results = results.order_by(field)

        if filters:
            for f in filters:
                results = results.filter(f)

        results = [e.to_json() for e in results.all()]

        if not results:
            return []

        # If the entity type is variant, we will fetch information on them in
        # the variants table.
        if results[0]["tested_entity"] == "variant":
            variants_dict = {}
            for var in self.session.query(genotype.Variant).all():
                variants_dict[var.name] = var

            for res in results:
                info = variants_dict.get(res["entity_name"]).to_json()
                if info is None:
                    msg = "Could not find variant {} in database.".format(
                        res["entity_name"]
                    )
                    raise ValueError(msg)

                res.pop("entity_name")
                res["variant"] = info

        return results

    def get_bonferonni(self, task_name, alpha):
        """Get the Bonferonni adjusted alpha for a given task."""
        try:
            n_tests, _ = self.session.query(
                sqlalchemy.func.count(
                    experiment.ExperimentResult.task_name
                ), experiment.ExperimentResult.task_name
            ).filter(
                experiment.ExperimentResult.task_name.like(task_name)       
            ).group_by(experiment.ExperimentResult.task_name).one()
        except Exception:
            return None

        return alpha / n_tests

    def get_configuration(self):
        if self.config is not None:
            with open(self.config, "r") as f:
                return f.read()

    def _fit_line(self, y, x):
        m, b, r, p, stderr = scipy.stats.linregress(x, y)
        return m, b


def initialize_application(experiment_name):
    """Initialize database connection and bind to the application context."""
    global www_backend
    www_backend = Backend(experiment_name)


@app.route(FORWARD_REPORT_ROOT)
def empty_report():
    return render_template("default.html", STATIC_ROOT=STATIC_ROOT)


@app.route(FORWARD_REPORT_ROOT + "/experiment/info.json")
def api_experiment_info():
    info = www_backend.info.copy()
    info["start_time"] = info["start_time"].strftime("%Y-%m-%d %H:%m:%S")
    info["walltime"] = format_time_delta(info["walltime"])
    return json.dumps(info)


@app.route(FORWARD_REPORT_ROOT + "/experiment/variants.json")
def api_get_variants():
    order_by = request.args.get("order_by", None)
    ascending = parse_bool(request.args.get("ascending", "true"))

    li = www_backend.get_variants(add_maf=True)
    if order_by is not None:
        li = sorted(li, key=lambda x: x[order_by], reverse=(not ascending))

    return json.dumps(li)


@app.route(FORWARD_REPORT_ROOT + "/experiment/variables.json")
def api_get_variables():
    var_type = request.args.get("type", None)
    order_by = request.args.get("order_by", None)
    ascending = parse_bool(request.args.get("ascending", "true"))

    return json.dumps(
        www_backend.get_variables(var_type=var_type, order_by=order_by,
                                  ascending=ascending)
    )


@app.route(FORWARD_REPORT_ROOT + "/experiment/exclusions.json")
def api_get_related_phenotypes_exclusions():
    order_by = request.args.get("order_by", None)
    ascending = parse_bool(request.args.get("ascending", "true"))

    # Parse into a list (easier to use from ReactJS).
    li = []
    exclusions = www_backend.get_related_phenotypes_exclusions()["exclusions"]
    for k in exclusions:
        d = exclusions[k]
        d.update({"phenotype": k})
        li.append(d)

    if order_by is not None:
        if order_by == "related":
            def key(x):
                return ",".join(x["related"])
        else:
            key = lambda x: x[order_by]

        li = sorted(li, key=key, reverse=(not ascending))

    return json.dumps(li)


@app.route(FORWARD_REPORT_ROOT + "/variables/data.json")
def api_get_outcome_vector():
    variable, transformation = _variable_arg_check(request)
    try:
        v = nan_to_none(
            www_backend.get_outcome_vector(variable, transformation)
        )
        return json.dumps(v)
    except ValueError:
        raise InvalidAPIUsage("Could not find variable {}.".format(variable))


@app.route(FORWARD_REPORT_ROOT + "/variables/plots/histogram.json")
def api_histogram():
    variable, transformation = _variable_arg_check(request)
    kwargs = {}
    bins = request.args.get("bins")
    if bins:
        kwargs["bins"] = int(bins)

    try:
        hist, edges = www_backend.get_variable_histogram(
            variable, transformation, **kwargs
        )
    except ValueError:
        raise InvalidAPIUsage("Could not find variable {}.".format(variable))
    return json.dumps({
        "hist": nan_to_none(hist),
        "edges": nan_to_none(edges)
    })


@app.route(FORWARD_REPORT_ROOT + "/variables/plots/normalqq.json")
def api_normal_qq():
    variable, transformation = _variable_arg_check(request)
    try:
        exp, obs, m, b = www_backend.get_variable_normal_qqplot(
            variable, transformation
        )
    except ValueError:
        raise InvalidAPIUsage("Could not find variable {}.".format(variable))

    return json.dumps({
        "expected": nan_to_none(exp),
        "observed": nan_to_none(obs),
        "xLimits": [np.min(exp), np.max(exp)],
        "yLimits": [np.min(obs), np.max(obs)],
        "m": m,
        "b": b
    })


@app.route(FORWARD_REPORT_ROOT + "/variables/plots/correlation_plot.json")
def api_correlation_plot():
    data, names = www_backend.get_variable_corrplot()
    return jsonify(data=[list(row) for row in data], names=names)


@app.route(FORWARD_REPORT_ROOT + "/experiment/tasks.json")
def api_tasks():
    tasks = www_backend.get_tasks()
    for i in range(len(tasks)):
        name, task_type = tasks[i].split("_")
        tasks[i] = {"name": name, "type": task_type}
    return jsonify(tasks=tasks)


@app.route(FORWARD_REPORT_ROOT + "/tasks/results.json")
def api_task_results():
    task = request.args.get("task")
    p_thresh = request.args.get("pthresh", 0.05)
    order_by = request.args.get("order_by", None)
    ascending = parse_bool(request.args.get("ascending", "true"))

    if task is None:
        raise InvalidAPIUsage("A 'task' parameter is expected.")

    task = "{}_%".format(task)  # Used to match without the type.
    filters = [
        experiment.ExperimentResult.significance <= p_thresh,
    ]

    sort_by_variant = False
    if order_by == "variant":
        order_by = None
        sort_by_variant = True

    results = www_backend.get_results(task, filters, order_by, ascending)

    if sort_by_variant:
        results = sorted(
            results,
            key=lambda x: x["variant"]["name"],
            reverse=(not ascending)
        )

    return jsonify(results=results)


@app.route(FORWARD_REPORT_ROOT + "/tasks/plots/qqpvalue.json")
def api_p_value_qqplot():
    task = request.args.get("task")
    if task is None:
        raise InvalidAPIUsage("A 'task' parameter is expected.")

    task = "{}_%".format(task)  # Used to match without the type.
    return json.dumps(www_backend.p_value_qq_plot(task))


@app.route(FORWARD_REPORT_ROOT + "/tasks/corrections/bonferonni.json")
def api_bonferonni():
    task = request.args.get("task")
    if task is None:
        raise InvalidAPIUsage("A 'task' parameter is expected.")

    alpha = request.args.get("alpha")
    try:
        alpha = float(alpha)
    except Exception:
        raise InvalidAPIUsage("A float 'alpha' parameter is expected.")

    task = "{}_%".format(task)  # Used to match without the type.
    return json.dumps({
        "alpha": www_backend.get_bonferonni(task, alpha)
    })


@app.route(FORWARD_REPORT_ROOT + "/tasks/logistic_section.html")
def task_rendered_logistic():
    task = request.args.get("task")
    if task is None:
        raise InvalidAPIUsage("A 'task' parameter is expected.")

    return render_template("logistictest.html", task=task)


@app.route(FORWARD_REPORT_ROOT + "/tasks/linear_section.html")
def task_rendered_linear():
    task = request.args.get("task")
    if task is None:
        raise InvalidAPIUsage("A 'task' parameter is expected.")

    return render_template("lineartest.html", task=task)


@app.route(FORWARD_REPORT_ROOT + "/experiment/yaml_configuration.html")
def api_get_yaml_configuration():
    """Returns a pygmentized version of the configuration file."""
    yaml = www_backend.get_configuration()
    return pygments.highlight(
        yaml,
        YamlLexer(),
        HtmlFormatter(linenos=True, cssclass="pygments-highlight")
    )


def _variable_arg_check(request):
    variable = request.args.get("name")
    transformation = request.args.get("transformation")
    if variable is None:
        raise InvalidAPIUsage("A 'name' parameter is expected.")
    return variable, transformation


class InvalidAPIUsage(Exception):
    def __init__(self, message, status_code=400, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidAPIUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def serve():
    app.run(debug=True)


def nan_to_none(li):
    li = list(li)
    for i, val in enumerate(li):
        if np.isnan(val):
            li[i] = None
    return li


def parse_bool(b):
    b = b.lower()
    if b == "true":
        b = True
    elif b == "false" or b == "":
        b = False
    else:
        raise ValueError("Can't parse bool from '{}'.".format(b))
    return b
