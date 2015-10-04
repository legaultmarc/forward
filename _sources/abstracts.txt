Extending `Forward`
====================

`Forward` was designed to be easily extensible. To achieve this, we have
adopted a modular structure and have developed abstract classes that serve as
template for the different components. Bioinformaticians can implement their
own versions of the phenotype and genotypes databases if they want to do
specific optimizations. They can also add new statistical tests by implementing
new Tasks.

This section describes what is expected of the implementations of abstract
classes.

Phenotype databases
--------------------

Phenotype databases should inherit :py:class:`forward.phenotype.db.AbstractPhenotypeDatabase`

.. autoclass:: forward.phenotype.db.AbstractPhenotypeDatabase
    :members:

Genotype databases
-------------------

Genotype databases should inherit :py:class:`forward.genotype.AbstractGenotypeDatabase`

.. autoclass:: forward.genotype.AbstractGenotypeDatabase
    :members:

Tasks
------

Tasks are classes that take care of statistical testing. Their ``run_task``
method will sequentially be called by the experiment.

.. autoclass:: forward.tasks.AbstractTask
    :members:
