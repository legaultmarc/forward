forward.fwdGLM = {};
var fwdGLM = forward.fwdGLM;

// Results Table
var GLMResultRow = React.createClass({
  render: function() {
    return (
      <tr>
        <td>{this.props.variant}</td>
        <td>{this.props.outcome}</td>
        <td>{this.props.p}</td>
        <td>
          {this.props.effect} [{this.props.effectLow} - {this.props.effectHigh}]
        </td>
      </tr>
    );
  }
});

var GLMResultsTable = React.createClass({
  getInitialState: function() {
    return {
      data: {"results": []},
      pThreshold: 0.05
    };
  },
  queryServer: function(task, threshold, callback) {
    $.ajax({
      url: "/tasks/results.json",
      data: {"task": task, "pthresh": threshold},
      success: function(data) { callback(data); }
    });
  },
  componentDidMount: function() {
    this.queryServer(this.props.task, this.state.pThreshold, function(data) {
      this.setState({data: data});  
    }.bind(this));
  },
  changeThreshold: function() {
    var thresh = window.prompt(
      "What should the new threshold be?", this.state.pThreshold
    );
    var newState = {pThreshold: parseFloat(thresh)};
    this.queryServer(this.props.task, thresh, function(data) {
      newState["data"] = data;
      this.setState(newState);
    }.bind(this));
  },
  render: function() {
    var resultNodes = this.state.data.results.map(function(d, i) {
      var fmt = d3.format(".3f");
      var effect;
      if (this.props.modelType == "logistic") effect = Math.exp(d.coefficient);
      else effect = d.coefficient;

      return (
        <GLMResultRow key={i} variant={d.variant.name}
           outcome={d.phenotype} p={d3.format(".3e")(d.significance)}
           effect={fmt(effect)}
           effectLow={fmt(Math.exp(d.confidence_interval_min))}
           effectHigh={fmt(Math.exp(d.confidence_interval_max))} />
      );
    }.bind(this));

    return (
      <div>
       <p className="caption">{this.props.children}</p>
       <p>
         The current p-value threshold is <a role="button"
          onClick={this.changeThreshold}>{this.state.pThreshold}</a>.
       </p>
       <table>
          <thead>
            <tr>
              <th>Variant</th>
              <th>Outcome</th>
              <th>p-value</th>
              <th>{ this.props.modelType == "logistic"? "OR": "Beta" } (95% CI)</th>
            </tr>
          </thead>
          <tbody>
            {resultNodes}
          </tbody>
       </table>
     </div>

    );
  }
});

fwdGLM.renderResultsTable = function(nodeId, taskName, modelType) {
  React.render(
    <GLMResultsTable task={taskName} modelType={modelType}>
      <strong>Table.</strong> Results from the {modelType} regression analysis
      of the described variables and outcomes.
    </GLMResultsTable>,
    document.getElementById(nodeId)
  );
};

fwdGLM.renderManhattan = function(nodeId, taskName, modelType) {
  var config = {
    width: 750,
    height: 340,
    effectLabel: modelType == "logistic"? "OR": "Beta"
  };

  // Get data.
  $.ajax({
    url: "/tasks/results.json",
    data: {"task": taskName, "pthresh": 1},
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
      manhattan(config, data, nodeId);
    }
  });

};

fwdGLM.renderQQPlot = function(nodeId, taskName) {
  var config = {
    width: 600,
    height: 400
  };

  // Get data.
  $.ajax({
    url: "/tasks/plots/qqpvalue.json",
    dataType: "json",
    data: {"task": taskName},
    success: function(data) {
      createQQ(config, data, nodeId);
    },
    error: function() {
      console.log("Fail parsing request for qq plot of p values.");
    }
  });

};

fwdGLM.renderSection = function(taskName, modelType) {
  // Results table.
  fwdGLM.renderResultsTable(taskName + "_results", taskName, modelType);

  // Manhattan plot.
  fwdGLM.renderManhattan(taskName + "_manhattan", taskName, modelType);

  // QQ plot.
  fwdGLM.renderQQPlot(taskName + "_qqplot", taskName, modelType);
};