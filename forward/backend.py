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

import json
import os

import sqlalchemy
from flask import Flask, request, url_for, render_template
app = Flask(__name__)

from . import SQLAlchemySession, genotype
from .experiment import Experiment
from .phenotype.variables import Variable


www_backend = None
BASE = os.path.abspath(os.path.dirname(__file__))


class Backend(object):
    """Class that provides all api functionality to be used for both report
       creation and the rest api.

    """

    def __init__(self, experiment_name):
        self.engine = Experiment.get_engine(experiment_name, "sqlite")
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

    def get_variants(self):
        variants = self.session.query(genotype.Variant).all()
        return [variant.to_json() for variant in variants]

    def get_variables(self):
        variables = self.session.query(Variable).all()
        return [variable.to_json() for variable in variables]


def initialize_application(experiment_name):
    """Initialize database connection and bind to the application context."""
    global www_backend
    www_backend = Backend(experiment_name)

@app.route("/")
def empty_report():
    with open(os.path.join(BASE, "static", "default.html"), "r") as f:
        return f.read()

@app.route("/variants.json")
def api_get_variants():
    return json.dumps(www_backend.get_variants())

@app.route("/variables.json")
def api_get_variables():
    return json.dumps(www_backend.get_variables())

def serve():
    app.run(debug=True)
