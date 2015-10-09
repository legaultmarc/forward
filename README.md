# Introduction

`Forward` is a python package that provides tools and utilities for _foward
genetics_ studies. It is currently under the very early stages of development.

# Documentation

Documentation can be created from the sphinx docs (run ``make html`` from the
``forward/docs`` directory.

Alternatively, a rendered version can be found 
__[here](http://legaultmarc.github.io/forward)__.

# Report

An demo of the interactive report can be
[found here](http://www.statgen.org/forward/fto). If you want to deploy your
own version to share results with collaborators, follow the instructions from
[the docs](http://legaultmarc.github.io/forward).

The quick and easy way to serve an experiment is to run this script:

```python
#!/usr/bin/env python

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import forward.backend

forward.backend.initialize_application("EXPERIMENT_NAME")

http_server = HTTPServer(WSGIContainer(forward.backend.app))
http_server.listen(5000)  # Set the port here
IOLoop.instance().start()
```

# Installation

This package will go on pypy following the first official release. In the
meantime, user's interested in the package should clone it and install it
from the source. Because it's still changing very fast and some critical
aspects are not fully implemented and tested, this package should not be used
for real studies (yet).
Note that the first official release is expected to be around the end of
October 2015.
