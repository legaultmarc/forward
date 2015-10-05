Forward's database
===================

Relational databases are automatically built to hold analysis results for any
experiment. This is done using `SQLAlchemy <http://www.sqlalchemy.org/>`_ an
`Object Relational Mapper` for Python. This package makes it easy to use one
of the many supported RDBMS backends while writing technology agnostic code. It
also maps database entries to Python objects which makes the integration
seamless and facilitates some technical aspects.

This section describes the different Python classes that will get translated to
database tables.


Variant table
--------------
.. autoclass:: forward.genotype.Variant
    :members:

Results tables
---------------
.. autoclass:: forward.experiment.ExperimentResult
    :members:

.. autoclass:: forward.tasks.LinearTestResults
    :members:
