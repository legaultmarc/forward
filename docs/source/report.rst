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

The backend can be used to do your analysis without leaving Python. This can be
useful if you're not interested in the dynamic report or if you want to do
something specific without worrying about integration in the web report.

A `documented example <https://github.com/legaultmarc/forward/blob/master/notebooks/Backend.ipynb>`_
can be found on Github. It is a Jupyter notebook showing how to do a QQ plot of
SKAT p-values using matplotlib. It is very simple and shows how to access data
and how to get help interactively.

For the interactive report, we use a Flask binding of most Backend methods.
These bindings make the Backend queryable using HTTP requests. The returned
data is either HTML (rarely) and json (most of the time).

Front-end
++++++++++

Introduction
""""""""""""

The interface for the report was built using modern web technologies. It
communicates with the backend using the Flask API (described above). The
tables are `react <https://facebook.github.io/react/>`_ components that take
care of querying the server and re-rendering themselves following user
interaction. Most of the plots are generated using `d3.js <d3js.org>`_, a
JavaScript framework for DOM manipulation that is very popular for data
visualization.

The javascript dependencies are managed using `Bower <http://bower.io>`_. All
the files are in the `forward/static` subdirectory of the repo. If you want
to extend the report without adding js dependencies, you don't need to take
care of Bower, because all of the required files are included in the repo. This
decision was made to make it easier for developers to play with the frond-end
without tedious configuration. If you want to update the js dependencies, you
may edit the ``bower.json`` file and run ``bower update``.

Nonetheless, front-end developers will need to build their javascript. This is
because `react` code uses `JSX` which needs to be converted to regular
javascript. Documentation for this step is available
`here <https://facebook.github.io/react/docs/getting-started.html>`_. To
summarize, you need to install babel:

.. code-block:: bash

    npm install --global babel

And then run the build command:

.. code-block:: bash

    cd forward/static/js
    babel src --watch --out-dir build

The ``--watch`` flag looks at activity on your filesystem and runs the
conversion as soon as something changes.

.. note::
    Extending the report is not easy. If you have feature requests, feel free
    to use the `issue tracker <https://github.com/legaultmarc/forward/issues>`_.
    You can also email us (`contact information
    <https://github.com/legaultmarc>`_ is available through github)
    with questions or comments.

Rendering Sections
"""""""""""""""""""

The report's home page is rendered using
`jinja2 <http://jinja.pocoo.org/docs/dev/>`_. The template for this page
is found in `forward/templates/default.html`.

This template is fairly empty. It loads some javascript and css, but it has
no content whatsoever. Notice the following piece of code:

.. code-block:: javascript

    // Get the tasks.
    $.getJSON(window.location.pathname + "/experiment/tasks.json", function(data) {
      var tasks = data.tasks;
      // For every task, fetch the html snippet.
      tasks.map(function(task) {
        forward.handleTask(task.type, task.name);
      });
      forward.xrefs.reNumber();
    });

This snippet (included in the `default.html` template) queries the tasks that
were executed in this experiment and calls the ``forward.handleTask`` function
to find an appropriate task handler. This function is basically a ``switch ...
case`` dispatching different handlers based on the task type.  Then, the
handler is responsible for populating the relavant report section.

Let's take linear regression as an example. It's handler is
``forward._handleLinear``. The latter do the following:

1. Create a new DOM element (a div) with id `section_TaskName`. It appends it
   to the results div.
2. It fetches an html snippet from the backend (in this case, it will request
   ``API_ROOT/tasks/linear_section.html`` from the API which will render
   ``forward/templates/lineartest.html``). This contains only a couple of DOM
   elements that are needed to hookup the dynamic tables and plots. The
   dispatch method will then include this piece of HTML as the ``innerHTML``
   of the div we created in step 1.
3. The dispatch method also triggers the javascript rendering function, in this
   case it is defined in ``section_glm.js``. This function call is finally
   responsible for rendering everything you see on screen.
