forward = {};

forward.withContinuousVariables = function(f) {
  $.getJSON(
    window.location.pathname + "/experiment/variables.json?type=continuous",
    function(data) { f(data); }
  );
};

/**
 * Data providers for dynamic tables.
 *
 * The data providers respond to actions that are triggered in response to
 * user interaction. They are responsible for updating the state of the table
 * after querying the server.
 *
 **/
forward._genericProviderFactory = function(config) {
  return function(action, argList) {
    if (this === window) {
      throw ("ValueError: The provider interface's 'this' variable should be " +
            "bound to the React component.");
    }

    var url = config.url;
    var dataCallback = config.dataCallback;
    var getParams = config.getParams || {};

    var requestData;
    switch(action.toLowerCase()) {
      case "init":
        requestData = getParams;
        break;

      case "sort":
        column = argList[0];
        ascending = argList[1];
        requestData = $.extend(getParams, {"order_by": column,
                                           "ascending": ascending});
    }

    $.ajax({
      url: url,
      dataType: "json",
      data: requestData,
      success: dataCallback.bind(this),
      error: function() {
        throw ("AjaxError: The request to get discrete variables " +
                "information failed.");
      }
    });
  };

};

/**
 * Format a p-value.
 **/
forward.formatPValue = function(p) {
  if (Math.abs(p) < 0.001) {
    // Use scientific notation.
    return d3.format(".3e")(p);
  }
  return d3.format(".3f")(p);
};

forward.discreteVariablesProvider = forward._genericProviderFactory({
  url: window.location.pathname + "/experiment/variables.json",
  getParams: {"type": "discrete"},
  dataCallback: function(data) {
    var columns = ["Name", "n controls", "n cases", "n missing", "Covariate"];
    var serverColumns = ["name", "n_controls", "n_cases", "n_missing",
                         "is_covariate"];
    data = data.map(function(d) {
      return serverColumns.map(function(k) { return d[k]; });
    });
    this.setState(
      {loading: false, serverColumns: serverColumns, columns: columns,
       data: data}
    );
  }
});

forward.variantProvider = forward._genericProviderFactory({
  url: window.location.pathname + "/experiment/variants.json",
  dataCallback: function(data) {
    var columns = ["Name", "Chrom", "Pos", "Minor", "Major", "MAC", "MAF",
                   "n missing", "n non missing"];

    var serverColumns = ["name", "chrom", "pos", "minor", "major", "mac",
                         "maf", "n_missing", "n_non_missing"];

    data = data.map(function(d) {
      return serverColumns.map(function(k) {
        switch(k) {
          case "maf":
            return d3.format(".3f")(d[k]);
          case "mac":
            return d3.format(".2f")(d[k]);
          default:
            return d[k];
        }
      });
    });
    this.setState(
      {loading: false, serverColumns: serverColumns, columns: columns,
       data: data}
    );
  }
});

forward.exclusionProvider = forward._genericProviderFactory({
  url: window.location.pathname + "/experiment/exclusions.json",
  dataCallback: function(data) {
    var threshold = forward.info.phenotype_correlation_for_exclusion;
    var columns = ["Phenotype", "Related phenotypes",
                   "n excluded (threshold: " + threshold + ")"];
    var serverColumns = ["phenotype", "related", "n_excluded"];

    data = data.map(function(d) {
      return serverColumns.map(function(k) {
        switch(k) {
          case "related":
            return d[k].join(", ");
          default:
            return d[k];
        }
      });
    });
    this.setState(
      {loading: false, serverColumns: serverColumns, columns: columns,
       data: data}
    );
  }
});

/**
 * Get metadata on the experiment and make it available to everyone.
 * FIXME this is dependant on the DOM loading. We need to wait for it.
 **/
forward.info = (function() {
  $.getJSON(window.location.pathname + "/experiment/info.json", function(data) {
    forward.info = data;

    // Also fill all the relevant dom placeholders.
    $(".fwdinfo").each(function(i, e) {

      classList = e.className.split(" ");
      for (var i = 0; i < classList.length; i++) {
        var key = classList[i];
        if (data[key]) {
          e.innerHTML = data[key];
          return;
        }
      }

    });

    // Add the YAML file if it's available.
    if (data.configuration) {
      $.get(
        window.location.pathname + "/experiment/yaml_configuration.html",
        function(data) {
          var node = document.createElement("div");
          node.id = "yaml-configuration";
          content = ("<p>The YAML configuration file used to describe this " +
                     "experiment is as follows:</p>");
          content += data;
          node.innerHTML = content;

          document.getElementById("annex").appendChild(node);
        }
      );
    }

  });
})();


/**
 * Create a figure object.
 **/
forward.Figure = function(name) {
  if (forward._figures === undefined) {
    forward._figures = {}  // Hash of name to dom element.
  }

  var fig = forward._figures[name]
  if (fig) {
    return fig;
  }

  // Create the DOM element.
  fig = document.createElement("div");
  forward._figures[name] = fig
  fig.id = name;

  // Create a 'x' that removes this div.
  var closeButton = document.createElement("a");
  closeButton.innerHTML = "&times;";
  closeButton.className = "close-figure";

  fig.appendChild(closeButton);

  document.getElementById("figures").appendChild(fig);

  closeButton.addEventListener("click", function() {
    delete forward._figures[fig.id];
    document.getElementById("figures").removeChild(fig);
  });

  return fig;
};

/**
 * Create a table object.
 **/
forward.Table = function(name) {
  // TODO implement me.
  that = {};

  if (forward._tables === undefined) {
    forward._tables = {}  // Hash of name to dom element.
  }

  that.number = 3;
  return that;
};

/**
 * Checks if a figure with the provided name already exists.
 **/
forward.figureExists = function(name) {
  if (forward._figures === undefined) return false;
  return forward._figures.hasOwnProperty(name);
};

forward.valuesLike = function(li, value) {
  if (value === undefined) value = 0;
  var out = new Array(li.length);
  for (var i = 0; i < li.length; i++) {
    out[i] = value;
  }
  return out;
};

forward.range = function(n) {
  return Array.apply(null, Array(n)).map(function(_, i) { return i; });
};

/**
 * Elementwise or vector addition.
 **/
forward.add = function(array, elem) {
  // If it's an array, we do element wise.
  if ($.isArray(elem)) {
    return array.map(function(e, i) {
      return e + elem[i];
    });
  }
  else {
    return array.map(function(e) {
      return e + elem
    });
  }
};

/**
 * Get task handler.
 **/
forward.handleTask = function(taskType, taskName) {
  switch (taskType) {
    case "LogisticTest":
      forward._handleLogistic(taskName);
      break;
    case "LinearTest":
      forward._handleLinear(taskName);
      break;
  }
};

forward._handleLogistic = function(taskName) {
  var node = document.createElement("div");
  node.id = "section_" + taskName;
  document.getElementById("results").appendChild(node);

  $.ajax({
    url: window.location.pathname + "/tasks/logistic_section.html",
    data: {"task": taskName},
    success: function(data) {
      node.innerHTML = data;
      fwdGLM.renderSection(taskName, "logistic");
    }
  });
};

forward._handleLinear = function(taskName) {
  var node = document.createElement("div");
  node.id = "section_" + taskName;
  document.getElementById("results").appendChild(node);

  $.ajax({
    url: window.location.pathname + "/tasks/linear_section.html",
    data: {"task": taskName},
    success: function(data) {
      node.innerHTML = data;
      fwdGLM.renderSection(taskName, "linear");
    }
  });
};
