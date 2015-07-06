#!/bin/bash

coverage run setup.py test
coverage html

if [ $(uname) == "Darwin" ]; then
    open htmlcov/index.html
fi
