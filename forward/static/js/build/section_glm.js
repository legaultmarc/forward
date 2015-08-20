/**
 * Module to display results from GLM (linear or logistic) regression.
 **/
forward.fwdGLM = {};
var fwdGLM = forward.fwdGLM;

// Results Table
var GLMResultRow = React.createClass({displayName: "GLMResultRow",
  render: function() {
    return (
      React.createElement("tr", null, 
        React.createElement("td", null, this.props.variant), 
        React.createElement("td", null, this.props.outcome), 
        React.createElement("td", null, this.props.p), 
        React.createElement("td", null, 
          this.props.effect, " [", this.props.effectLow, " - ", this.props.effectHigh, "]"
        )
      )
    );
  }
});

var GLMResultsTable = React.createClass({displayName: "GLMResultsTable",
  getInitialState: function() {
    return {
      data: {"results": []},
      pThreshold: null,
      humanThreshold: ""  // Human readable version of the threshold.
    };
  },
  queryServer: function(task, threshold, callback) {
    $.ajax({
      url: window.location.pathname + "/tasks/results.json",
      data: {"task": task, "pthresh": threshold},
      success: function(data) { callback(data); }
    });
  },
  withBonferonni: function(task, alpha, callback) {
    $.ajax({
      url: window.location.pathname + "/tasks/corrections/bonferonni.json",
      dataType: "json",
      data: {"task": task, "alpha": alpha},
      success: function(data) { callback(data); }
    });
  },
  guessFormat: function(p) {
    return (p > 0.001) ? d3.format(".3f")(p): d3.format(".3e")(p);
  },
  componentDidMount: function() {
    // Get the bonferonni correction.
    var task = this.props.task;

    this.withBonferonni(task, 0.05, function(p) {
      p = p["alpha"];

      this.queryServer(task, p, function(data) {
        this.setState({
          data: data,
          pThreshold: p,
          humanThreshold: "Bonferonni (" + this.guessFormat(p) + ")"
        });
      }.bind(this));

    }.bind(this));

  },
  changeThreshold: function() {
    var thresh = window.prompt(
      "What should the new threshold be (leave empty for Bonferonni)?",
      this.guessFormat(this.state.pThreshold).toString()
    );
    var task = this.props.task;
    var p = parseFloat(thresh);
    if (p) {
      var newState = {
          pThreshold: p,
          humanThreshold: this.guessFormat(p).toString()
      };
      this.queryServer(task, thresh, function(data) {
        newState["data"] = data;
        this.setState(newState);
      }.bind(this));
    }
    else {
      // Default to Bonferonni.
      this.withBonferonni(task, 0.05, function(p) {
        p = p["alpha"];
        var newState = {
            pThreshold: p,
            humanThreshold: "Bonferonni (" + this.guessFormat(p) + ")"
        };

        this.queryServer(task, p, function(data) {
          newState["data"] = data;
          this.setState(newState);
        }.bind(this));

      }.bind(this));

    }
  },
  render: function() {
    var resultNodes = this.state.data.results.map(function(d, i) {
      var fmt = d3.format(".3f");
      var effect;
      if (this.props.modelType == "logistic") effect = Math.exp(d.coefficient);
      else effect = d.coefficient;

      return (
        React.createElement(GLMResultRow, {key: i, variant: d.variant.name, 
           outcome: d.phenotype, p: d3.format(".3e")(d.significance), 
           effect: fmt(effect), 
           effectLow: fmt(Math.exp(d.confidence_interval_min)), 
           effectHigh: fmt(Math.exp(d.confidence_interval_max))})
      );
    }.bind(this));

    return (
      React.createElement("div", null, 
       React.createElement("p", {className: "caption"}, this.props.children), 
       React.createElement("p", null, 
         "The current p-value threshold is ", React.createElement("a", {role: "button", 
          onClick: this.changeThreshold}, this.state.humanThreshold), "."
       ), 
       React.createElement("table", null, 
          React.createElement("thead", null, 
            React.createElement("tr", null, 
              React.createElement("th", null, "Variant"), 
              React.createElement("th", null, "Outcome"), 
              React.createElement("th", null, "p-value"), 
              React.createElement("th", null,  this.props.modelType == "logistic"? "OR": "Beta", " (95% CI)")
            )
          ), 
          React.createElement("tbody", null, 
            resultNodes
          )
       )
     )

    );
  }
});

fwdGLM.renderResultsTable = function(nodeId, taskName, modelType) {
  React.render(
    React.createElement(GLMResultsTable, {task: taskName, modelType: modelType}, 
      React.createElement("strong", null, "Table."), " Results from the ", modelType, " regression analysis" + ' ' +
      "of the described variables and outcomes."
    ),
    document.getElementById(nodeId)
  );
};

fwdGLM.renderManhattan = function(config) {
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
        return {
          "outcome": d.phenotype,
          "variant": d.variant.name,
          "p": d.significance,
          "effect": Math.exp(d.coefficient),
          "position": d.variant.pos
        };
      });
      manhattan(plot_config, data, config.nodeId);
    }
  });

};

fwdGLM.renderQQPlot = function(config) {
  var plot_config = {
    width: 600,
    height: 400,
    phenotypeScale: config.phenotypeScale
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
      console.log("Fail parsing request for qq plot of p values.");
    }
  });

};

fwdGLM.renderSection = function(taskName, modelType) {

  // Create a phenotype colormap for this section.
  var phenotypeScale = d3.scale.category20();

  // Results table.
  fwdGLM.renderResultsTable(taskName + "_results", taskName, modelType);

  // Manhattan plot.
  var config = {
    nodeId:  taskName + "_manhattan",
    taskName: taskName,
    modelType: modelType,
    phenotypeScale: phenotypeScale
  };
  fwdGLM.renderManhattan(config);

  // QQ plot.
  config["nodeId"] = taskName + "_qqplot";
  fwdGLM.renderQQPlot(config);
};
