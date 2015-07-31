forward.fwdLogistic = {};
var fwdLogistic = forward.fwdLogistic;

// Results Table
var LogisticResultRow = React.createClass({
  render: function() {
    return (
      <tr>
        <td>{this.props.variant}</td>
        <td>{this.props.outcome}</td>
        <td>{this.props.p}</td>
        <td>{this.props.oddsRatio} [{this.props.orLow} - {this.props.orHigh}]</td>
      </tr>
    );
  }
});

var LogisticResultsTable = React.createClass({
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
      return (
        <LogisticResultRow key={i} variant={d.variant.name}
           outcome={d.phenotype} p={d3.format(".3e")(d.significance)}
           oddsRatio={fmt(Math.exp(d.coefficient))}
           orLow={fmt(Math.exp(d.confidence_interval_min))}
           orHigh={fmt(Math.exp(d.confidence_interval_max))} />
      );
    });

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
              <th>OR (95% CI)</th>
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

fwdLogistic.renderResultsTable = function(nodeId, taskName) {
  React.render(
    <LogisticResultsTable task={taskName}>
      <strong>Table.</strong> Results from the logistic regression analysis of
      the described variables and outcomes.
    </LogisticResultsTable>,
    document.getElementById(nodeId)
  );
};

fwdLogistic.renderManhattan = function(nodeId, taskName) {
  var config = {
    width: 750,
    height: 340
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

fwdLogistic.renderSection = function(taskName) {
  // Results table.
  fwdLogistic.renderResultsTable(taskName + "_results", taskName);

  // Manhattan plot.
  fwdLogistic.renderManhattan(taskName + "_manhattan", taskName);
};
