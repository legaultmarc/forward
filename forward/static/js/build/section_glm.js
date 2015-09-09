/**
 * Module to display results from GLM (linear or logistic) regression.
 **/
forward.fwdGLM = {};
var fwdGLM = forward.fwdGLM;

fwdGLM.resultsProviderFactory = function(task, taskType) {

  if (!task) {
    throw "A 'task' parameter is required.";
  }
  if (!taskType) {
    throw "A 'taskType' parameter is required.";
  }

  var columns = ["Variant", "Outcome", "p-value *"];
  var serverColumns = ["variant", "phenotype", "significance", "coefficient"];

  if (taskType === "linear") {
    columns.push("\u03B2 (95% CI)");

    serverColumns.push("std_beta");
    columns.push(React.createElement("span", null, "\u03B2", React.createElement("sup", null, "*"), " (95% CI)"));

    serverColumns.push("adjusted_r_squared");
    columns.push(React.createElement("span", null, "R", React.createElement("sup", null, "2")));


  }
  else if (taskType === "logistic") {
    columns.push("OR (95% CI)");
  }

  var threshold;
  var isBonferonni;
  var reactRef;

  var provider = function(action, argList) {
    if (threshold === undefined) {
      throw "Initialize the threshold first using setThreshold().";
    }

    var requestData = {};

    switch(action.toLowerCase()) {
      case "init":
        reactRef = this;
        break;

      case "update":
        break;

      case "sort":
        column = argList[0];
        ascending = argList[1];
        requestData = $.extend(requestData, {"order_by": column,
                                             "ascending": ascending});
        break;
    }

    $.ajax({
      url: window.location.pathname + "/tasks/results.json",
      data: $.extend(requestData, {"task": task, "pthresh": threshold}),
      success: function(data) {
        data = data.results;

        data = data.map(function(datum) {
          return serverColumns.map(function(k) {
            var value = datum[k];

            // Format numbers.
            switch (k) {
              case "coefficient":
                var effectMin = datum["confidence_interval_min"];
                var effectMax = datum["confidence_interval_max"];
                if (taskType === "logistic") {
                  value = Math.exp(value);
                  effectMin = Math.exp(effectMin);
                  effectMax = Math.exp(effectMax);
                }
                value = d3.format(".3f")(value);
                effectMin = d3.format(".3f")(effectMin);
                effectMax = d3.format(".3f")(effectMax);
                value = value + " [" + effectMin + " - " + effectMax + "]"; 
                break;
              case "std_beta":
                var low = datum["std_beta_min"];
                var high = datum["std_beta_max"];

                value = d3.format(".3f")(value);
                low = d3.format(".3f")(low);
                high = d3.format(".3f")(high);
                value = value + " [" + low + " - " + high + "]";
                break
              case "significance":
                value = forward.formatPValue(value);
                break;
              case "adjusted_r_squared":
                value = d3.format(".3f")(value);
                break;
              case "variant":
                value = value.name;
            }

            return value;
          });
        });

        // Set state.
        reactRef.setState({loading: false, serverColumns: serverColumns, 
                           columns: columns, data: data});
      }
    });
  } // Provider.

  return {
    "provider": provider,
    "setThreshold": function(t) { threshold=t; },
    "getThreshold": function() { return threshold; },
    "isBonferonni": function(b) {
      if (b === undefined) {
        return isBonferonni;
      } 
      else {
        isBonferonni = b;
      }
    },
  }

}

fwdGLM.renderResultsTable = function(nodeId, taskName, modelType) {
  var provider = fwdGLM.resultsProviderFactory(taskName, modelType);
  var bonferonni;

  // Create another div for the controls (we can't use the same as the table
  // because react will complain that we're messing with the DOM.
  var root = document.getElementById(nodeId);

  // Register for easier cross-referencing.
  forward.xrefs.register(root, "table");

  var reactTable = document.createElement("div");
  root.appendChild(reactTable);

  var controls = document.createElement("div");
  root.appendChild(controls);

  // Set the threshold to the bonferonni correction.
  $.ajax({
    url: window.location.pathname + "/tasks/corrections/bonferonni.json",
    dataType: "json",
    data: {"task": taskName, "alpha": 0.05},
    success: function(data) {
      bonferonni = data.alpha;
      provider.setThreshold(bonferonni);
      provider.isBonferonni(true);

      React.render(
        React.createElement(GenericTable, {provider: provider.provider}, 
          React.createElement("strong", null, "Table ", forward.xrefs.getJSXXref(root.id), "."), " Results from the ", modelType, " regression analysis of the described variables and outcomes."
        ),
        reactTable
      );

      add_controls(controls);

    }
  });

  var add_controls = function(node) {
    var threshold = forward.formatPValue(provider.getThreshold());
    if (provider.isBonferonni()) {
      threshold += " (Bonferonni &alpha;=0.05)";
    }

    var description = document.createElement("p");
    var thresholdNode = document.createElement("span");
    thresholdNode.innerHTML = threshold + " ";
    description.innerHTML = "<sup>*</sup> <em>p</em>-values with &alpha; &leq; ";
    description.appendChild(thresholdNode);
    node.appendChild(description);

    var button = document.createElement("a");
    button.className = "button";
    button.innerHTML = "Change threshold";
    description.appendChild(button);

    $(button).click(function() {
      var thresh = window.prompt(
        "What should the new threshold be (leave empty for Bonferonni)?",
        forward.formatPValue(provider.getThreshold())
      );

      if (thresh == "") {
        // Set bonferonni.
        provider.setThreshold(bonferonni);
        provider.isBonferonni(true);
        provider.provider("update");
        thresholdNode.innerHTML = bonferonni + " (Bonferonni &alpha;=0.05) ";
      }
      else {
        thresh = parseFloat(thresh);
        // Setting the numeric threshold.
        if (thresh) {
          provider.setThreshold(thresh);
          provider.isBonferonni(false);
          provider.provider("update");
          thresholdNode.innerHTML = thresh + " ";
        }
      }

    });
  };

};

fwdGLM.renderManhattan = function(config) {
  var node = document.getElementById(config.nodeId);
  forward.xrefs.register(node, "figure");
  node.innerHTML = (
    "<p class='caption'><strong>Figure " + 
    forward.xrefs.getXref(config.nodeId) + "</strong>. " +
    "Plot of association p-values with respect to genomic position or " +
    "effect size (interactive toggle)."
  ) + node.innerHTML;

  var plot_config = {
    width: 750,
    height: 340,
    effectLabel: config.modelType == "logistic"? "OR": "Beta",
    phenotypeScale: config.phenotypeScale
  };

  // Get data.
  $.ajax({
    url: window.location.pathname + "/tasks/results.json",
    data: {"task": config.taskName, "pthresh": 1},
    success: function(data) {
      // Format data.
      data = data["results"].map(function(d) {
        var res = {
          "pk": d.pk,
          "outcome": d.phenotype,
          "variant": d.variant.name,
          "p": d.significance,
          "effect": d.coefficient,
          "position": d.variant.pos
        };
        if (config.modelType == "logistic") {
          res.effect = Math.exp(res.effect);
        }

        return res;

      });
      manhattan(plot_config, data, config.nodeId);
    }
  });

};

fwdGLM.renderQQPlot = function(config) {
  var node = document.getElementById(config.nodeId)
  forward.xrefs.register(node, "figure");
  node.innerHTML += (
    "<p class='caption'><strong>Figure " +
    forward.xrefs.getXref(config.nodeId) + "</strong>. " +
    "Quantile-Quantile plot of association p-values with respect to the " +
    "uniform distribution."
  );

  var plot_config = {
    width: 600,
    height: 400,
    phenotypeScale: config.phenotypeScale,
    modelType: config.modelType
  };

  // Get data.
  $.ajax({
    url: window.location.pathname + "/tasks/plots/qqpvalue.json",
    dataType: "json",
    data: {"task": config.taskName},
    success: function(data) {
      createQQ(plot_config, data, config.nodeId);
    },
    error: function() {
      throw "Fail parsing request for qq plot of p values.";
    }
  });

};

fwdGLM.renderSection = function(taskName, modelType) {

  // Create a phenotype colormap for this section.
  var phenotypeScale = d3.scale.category20();

  // Results table.
  fwdGLM.renderResultsTable(taskName + "_results", taskName, modelType);

  // Manhattan plot.
  var manhattan_config = {
    nodeId:  taskName + "_manhattan",
    taskName: taskName,
    modelType: modelType,
    phenotypeScale: phenotypeScale
  };
  fwdGLM.renderManhattan(manhattan_config);

  // QQ plot.
  var qq_config = {
    nodeId:  taskName + "_qqplot",
    taskName: taskName,
    modelType: modelType,
    phenotypeScale: phenotypeScale
  };
  fwdGLM.renderQQPlot(qq_config);

  window.setTimeout(forward.xrefs.reNumber, 1500);

};
