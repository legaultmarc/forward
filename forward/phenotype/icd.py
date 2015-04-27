# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
International Classification of Diseases (ICD) bindings to annotate biological
databases.

You can download the ICD-10-CM here: http://www.cdc.gov/nchs/icd/icd10cm.htm

An archived copy is automatically used by this package.

In a given project, the user need to provide an yaml file with all the relevant
data to construct the database. If available, the IDC codes should be provided.
If they are, they will be matched against the provided IDC database in order
to automatically generate the annotations.

"""
