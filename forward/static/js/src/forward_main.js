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
 * Module to handle crossreferences.
 **/
forward.xrefs = (function() {

  var _counts = {
    "figure": 1,
    "table": 1,
    "reference": 1
  }; // Counters that are incremented when creating new xrefs.
  var _xrefs = {};
  var _types = {};

  /**
   * Create a crossreferenceable div.
   *
   * type is either "figure", "table" or "reference".
   * name is the unique name for this element.
   * closeButton is a bool indicating if a x button should be added to remove
   * the div.
   **/
  var create = function(type, name, closeButton) {
    if (_xrefs[name]) {
      throw "ValueError: '" + name + "' is already used.";
    }

    if (closeButton === undefined) {
      closeButton = false;
    }

    switch (type) {
      case "figure":
        return _create_element(name, "figure", closeButton);
      case "table":
        return _create_element(name, "table", closeButton);
      case "reference":
        return _create_reference(name);
      default:
        throw "Unknown type '" + type + "'";
    }
  };

  var _create_element = function(name, type, closeButton) {
    var node = document.createElement("div");
    node.id = name;
    node.className = "xref-" + type;
    node.number = _counts[type];

    var anchor = document.createElement("a");
    anchor.name = name;
    node.appendChild(anchor);

    _counts[type] += 1;

    if (closeButton) _add_close(node);

    _xrefs[name] = node;
    _types[name] = type;

    return node;
  };

  var _create_reference = function(name, closeButton) {
    throw "NotImplementedError";
  };

  var _add_close = function(node) {
    var closeButton = document.createElement("a");
    closeButton.innerHTML = "&times;";
    closeButton.className = "close-figure";

    node.appendChild(closeButton);

    closeButton.addEventListener("click", function() {
      var parentNode = node.parentNode;
      parentNode.removeChild(node);
    });

  };

  /**
   * Register an already existing node element.
   **/
  var register = function(node, type) {
    var name = node.id;
    if (!name) {
      throw "Error: Only DOM nodes with an id can be registered as xrefs.";
    }
    node.number = _counts[type];
    _counts[type] += 1;
    _xrefs[name] = node;
    _types[name] = type;
    $(node).addClass("xref-" + type);
  };

  /**
   * Renumber all xrefs according to a dom traversal.
   **/
  var reNumber = function() {
    _counts = {"table": 1, "figure": 1, "reference": 1};
    var nameExtractor = /xref-(\S+)/;

    $(".xref").each(function(idx, n) {
      // Parse the name.
      var classes = n.className;
      var name = nameExtractor.exec(classes)[0].substring(5);

      var type = _types[name];
      var node = _xrefs[name];
      if (node === undefined || type === undefined) {
        throw "Unknown crossreference '" + name + "'";
      }

      node.number = _counts[type];
      _counts[type] += 1;

      n.innerHTML = node.number;

    });

    $(".xref-link").each(function(_, n) {
      var classes = n.className;

      // remove the xref-link class.
      classes = classes.replace(/xref-link/, "")
      var name = nameExtractor.exec(classes)[0].substring(5);

      var type = _types[name];
      var node = _xrefs[name];

      n.innerHTML = capitalized(type) + " " + node.number;

    });
  };

  /**
   * Get a reference which is a span with the proper class to be tracked by
   * the cross reference system.
   **/
  var getXref = function(name) {
    var n = _xrefs[name].number;
    return "<span class='xref xref-" + name + "'>" + n + "</span>"
  };

  var getJSXXref = function(name) {
    var node = _xrefs[name];
    if (!node) {
      throw "Could not find registered xref with name '" + name + "'";
    }
    return (
      <span className={"xref xref-" + name}>{node.number}</span>
    );
  };

  var exists = function(name) {
    return (!_xrefs[name] === undefined);
  };

  return {
    "create": create,
    "register": register,
    "exists": exists,
    "reNumber": reNumber,
    "getXref": getXref,
    "getJSXXref": getJSXXref
  };

})();

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

capitalized = function(s) {
  return s[0].toUpperCase() + s.slice(1);
}
