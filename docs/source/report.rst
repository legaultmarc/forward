Interactive report
###################

To help visualize and explore experiment results, an interactive report comes
with `Forward`. This report is built on top of the
:py:class:`forward.backend.Backend` which parses analysis results in standard
Python data structures.

Run the server
---------------

To run the server, the simplest alternative is to use the provided command-line
interface (`scripts/forward-cli.py`).

.. code-block:: bash

    $ forward-cli.py report experiment_name

.. note::
    The current working directory needs to contain the experiment folder to
    use this command.

Alternative method for sharing
+++++++++++++++++++++++++++++++

If you want to share the report with colleagues, or host it on a website after
publication, it is best to use a more robust web server. The following script
can be used:

.. code-block:: python
    :linenos:

    #!/usr/bin/env python

    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    import forward.backend

    forward.backend.initialize_application("EXPERIMENT_NAME")

    http_server = HTTPServer(WSGIContainer(forward.backend.app))
    http_server.listen(5000)  # Set the port here
    IOLoop.instance().start()

It is also a good idea to use a process control system like `supervisord
<http://supervisord.org/>`_ when hosting the report on a server.

Extending the dynamic report
-----------------------------

Backend
++++++++

Add an example analysis using only the Python backend.

Front-end
++++++++++

