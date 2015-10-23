Available Components
====================

`Forward` experiments use three modular components to standardize access to
genetes, phenotypes and statistical testing. Some components are built-in with
`Forward` and are compatible with common data formats (described here).

Also note that you can write and use your own implementations. Simply follow
the instructions from the :ref:`abstracts` section.

Tasks
------

+----------------------------------------+--------------------+---------------------+--------------+---------------------------------------+
| class                                  | parameters         | variant type        | outcome type | reference                             |
+========================================+====================+=====================+==============+=======================================+
| :py:class:`forward.tasks.LinearTest`   | - outcomes         | common (MAF < 0.05) | continuous   |                                       |
|                                        | - covariates       |                     |              |                                       |
|                                        | - variants         |                     |              |                                       |
|                                        | - correction       |                     |              |                                       |
|                                        | - alpha            |                     |              |                                       |
+----------------------------------------+--------------------+---------------------+--------------+---------------------------------------+
| :py:class:`forward.tasks.LogisticTest` | - outcomes         | common (MAF < 0.05) | discrete     |                                       |
|                                        | - covariates       |                     |              |                                       |
|                                        | - variants         |                     |              |                                       |
|                                        | - correction       |                     |              |                                       |
|                                        | - alpha            |                     |              |                                       |
+----------------------------------------+--------------------+---------------------+--------------+---------------------------------------+
| :py:class:`forward.tasks.SKATTest`     | - outcomes         | Sets of variants.   | discrete or  | `website                              |
|                                        | - covariates       | Can test rare or    | continuous   | <http://www.hsph.harvard.edu/skat/>`_ |
|                                        | - variants         | common.             |              |                                       |
|                                        | - correction       |                     |              |                                       |
|                                        | - alpha            |                     |              |                                       |
|                                        | - **snp_set_file** |                     |              |                                       |
+----------------------------------------+--------------------+---------------------+--------------+---------------------------------------+


Genotype containers
--------------------

+-----------------------------------------------------+-----------------------+----------------+--------------------------------------------------+
| class                                               | parameters            | file type      | Notes                                            |
+=====================================================+=======================+================+==================================================+
| :py:class:`forward.genotype.MemoryImpute2Geno`      | - filter_name         | Small impute2  | This container load the genotype file in memory. |
|                                                     | - filter_maf          | files          | It is fast, but not suitable for large files.    |
|                                                     | - filter_completion   |                | IMPUTE2 file parsing is done using               |
|                                                     | - filename            |                | `gepyto <http://github.org/legaultmarc/gepyto>`_ |
|                                                     | - samples             |                |                                                  |
|                                                     | - filter_probability  |                |                                                  |
+-----------------------------------------------------+-----------------------+----------------+--------------------------------------------------+
| :py:class:`forward.genotype.PlinkGenotypeDatabase`  | - prefix              | Binary plink   | This container uses `pyplink                     |
|                                                     | - filter_maf          | files (bed, bim| <http://github.org/lemieuxl/pyplink>`_ to parse  |
|                                                     | - filter_completion   | , fam)         | the binary plink files.                          |
+-----------------------------------------------------+-----------------------+----------------+--------------------------------------------------+


Phenotype containers
---------------------

+------------------------------------+-------------------------+-----------------+--------------------------------------------------------------+
| class                              | parameters              | file_type       | Notes                                                        |
+====================================+=========================+=================+==============================================================+
| :py:class:`CSVPhenotypeDatabase`   | - filename              | delimited files | This is an implementation of                                 |
|                                    | - sample_column         | (e.g. CSV, TSV) | :py:class:`forward.phenotype.db.PandasPhenotypeDatabase`.    |
|                                    | - sep                   |                 | Most of the parameters are passed to the Pandas parser. You  |
|                                    | - compression           |                 | can refer to                                                 |
|                                    | - header                |                 | `their docs <http://bit.ly/1LrM3Co>`_ for more information.  |
|                                    | - skiprows              |                 |                                                              |
|                                    | - names                 |                 |                                                              |
|                                    | - na_values             |                 |                                                              |
|                                    | - decimal               |                 |                                                              |
|                                    | - exclude_correlated    |                 |                                                              |
+------------------------------------+-------------------------+-----------------+--------------------------------------------------------------+
| :py:class:`ExcelPhenotypeDatabase` | - filename              | Excel files     | This is an implementation of                                 |
|                                    | - sample_column         |                 | :py:class:`forward.phenotype.db.PandasPhenotypeDatabase`.    |
|                                    | - missing_values        |                 |                                                              |
|                                    | - exclude_correlated    |                 |                                                              |
+------------------------------------+-------------------------+-----------------+--------------------------------------------------------------+

Python documentation
---------------------

Tasks
""""""

.. automodule:: forward.tasks
    :members: LinearTest, LogisticTest, SKATTest

Genotype containers
""""""""""""""""""""

.. automodule:: forward.genotype
    :members: MemoryImpute2Geno, PlinkGenotypeDatabase

Phenotype containers
""""""""""""""""""""

.. automodule:: forward.phenotype.db
    :members: CSVPhenotypeDatabase, ExcelPhenotypeDatabase
