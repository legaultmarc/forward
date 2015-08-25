// Variables Table
var ContinuousVariableRow = React.createClass({displayName: "ContinuousVariableRow",
  buildModal: function() {

    document.getElementById("variable-modal").innerHTML = "";
    var modal = React.render(
      React.createElement(Modal, {title: this.props.name}, 
        React.createElement(ContinuousVariablePlotForm, {name: this.props.name, 
         transformation: this.props.transformation})
      ),
      document.getElementById("variable-modal")
    );
    modal.show();

  },
  render: function() {
      return (
        React.createElement("tr", null, 
          React.createElement("td", null, this.props.name), React.createElement("td", null, this.props.mean.toFixed(3)), 
          React.createElement("td", null, this.props.std.toFixed(3)), React.createElement("td", null, this.props.nmissing), 
          React.createElement("td", null, this.props.transformation ? this.props.transformation: "none"), 
          React.createElement("td", null, this.props.covariate), 
          React.createElement("td", null, 
            React.createElement("a", {className: "button", role: "button", onClick: this.buildModal}, "generate plot")
          )
        )
      )
  }
});

var ContinuousVariableTable = React.createClass({displayName: "ContinuousVariableTable",
  getInitialState: function() {
    return {data: []};
  },
  componentDidMount: function() {
    forward.withContinuousVariables(function(data) {
      this.setState({"data": data})
    }.bind(this));
  },
  render: function() {
    var nodes = []
    var data = this.state.data
    for (var i = 0; i < data.length; i++) {
      var v = data[i]
      nodes.push(
        React.createElement(ContinuousVariableRow, {key: i, name: v.name, std: v.std, 
          mean: v.mean, covariate: v.is_covariate ? "yes": "no", 
          transformation: v.transformation, nmissing: v.n_missing})
      )
    }

    return (
      React.createElement("div", null, 
        React.createElement("p", {className: "caption"},  this.props.children), 
        React.createElement("table", null, 
          React.createElement("thead", null, 
            React.createElement("tr", null, 
              React.createElement("th", null, "Name"), 
              React.createElement("th", null, "Mean"), 
              React.createElement("th", null, "Std"), 
              React.createElement("th", null, "n missing"), 
              React.createElement("th", null, "transformation"), 
              React.createElement("th", null, "covariate"), 
              React.createElement("th", null, "plots")
            )
          ), 
          React.createElement("tbody", null, 
            nodes
          )
        )
      )
    );
  }
});

var ContinuousVariablePlotForm = React.createClass({displayName: "ContinuousVariablePlotForm",
  handleSubmit: function(e) {
    e.preventDefault();

    for (ref in this.refs) {
      var node = React.findDOMNode(this.refs[ref])
      if (node.checked) {

        var figName = this.props.name + node.value;

        if (forward.figureExists(figName)) { continue; }

        var figure = forward.Figure(figName);

        var config = {
          "figure": figure,
          "variable": this.props.name,
          "transformation": null,
          "bins": 50,
          "xLabel": "",
          "yLabel": "",
          "width": 500,
          "height": 200,
          "fillColor": "#781B1F"
        };

        var plotFunction;
        switch(node.value) {
          case "hist":
            plotFunction = forward.variableHist;
            config.xLabel = this.props.name;
            config.yLabel = "Number of occurences (n)"
            break;

          case "histt":
            config.transformation = this.props.transformation;
            config.xLabel = this.props.name + " (transformed)";
            config.yLabel = "Number of occurences (n)"
            plotFunction = forward.variableHist;
            break;

          case "QQ":
            config.xLabel = "expected"
            config.yLabel = "observed"
            config.width = 400;
            config.height = 400;
            config.fillColor = "#000000";
            plotFunction = forward.variableNormalQQ;
            break;

          case "QQt":
            config.transformation = this.props.transformation;
            config.xLabel = "expected"
            config.yLabel = "observed (transformed)"
            config.width = 400;
            config.height = 400;
            config.fillColor = "#000000";
            plotFunction = forward.variableNormalQQ;
            break;

        }

        plotFunction(config)

      }
    }

    React.unmountComponentAtNode(document.getElementById("variable-modal"));
    if (figure) figure.scrollIntoView();
  },
  render: function() {
    var transformed_form_elements;
    if (this.props.transformation) {
      transformed_form_elements = (
        React.createElement("fieldset", null, 
          React.createElement("legend", null, "Plots for transformed variables"), 
          React.createElement("input", {type: "checkbox", name: "plots", value: "histt", id: "histt", ref: "histt"}), 
          React.createElement("label", {htmlFor: "histt"}, "Histogram (transformed)"), 

          React.createElement("input", {type: "checkbox", name: "plots", value: "QQt", id: "QQt", ref: "QQt"}), 
          React.createElement("label", {htmlFor: "QQt"}, "Normal QQ plot (transformed)")
        )
      );
    }
    return (
      React.createElement("form", {onSubmit: this.handleSubmit, className: "plot-form"}, 
        React.createElement("fieldset", null, 
          React.createElement("legend", null, "Plot types"), 
          React.createElement("input", {type: "checkbox", name: "plots", value: "hist", id: "hist", ref: "hist"}), 
          React.createElement("label", {htmlFor: "hist"}, "Histogram"), 

          React.createElement("input", {type: "checkbox", name: "plots", value: "QQ", id: "QQ", ref: "QQ"}), 
          React.createElement("label", {htmlFor: "QQ"}, "Normal QQ plot")
        ), 
         transformed_form_elements, 
        React.createElement("input", {type: "submit", value: "Generate plots", className: "button"})
      )
    );
  }
});

// Modal box.
var Modal = React.createClass({displayName: "Modal",
  getInitialState: function() {
    return {visible: false};
  },
  hide: function() {
    if (this.isMounted()) {
      this.setState({visible: false});
      $(document.body).off("keydown");
    }
  },
  show: function() {
    if (this.isMounted()) {
      this.setState({visible: true});
    }
  },
  componentDidMount: function() {
    $(document.body).on("keydown", this.keyClose)
  },
  keyClose: function(e) {
    if (e.keyCode === 27) {
      this.hide();
    }
  },
  render: function() {
    return (
      React.createElement("div", {className: "modal-wrapper", 
           style: {"display": this.state.visible ? "block": "none"}}, 
        React.createElement("div", {className: "modal-overlay"}), 
        React.createElement("div", {className: "modal"}, 
          React.createElement("a", {role: "button", onClick: this.hide, className: "close"}, "×"), 
          React.createElement("h2", null, this.props.title), 
          this.props.children
        )
      )
    );
  }
});

// Generic table
var GenericTable = React.createClass({displayName: "GenericTable",
  getInitialState: function() {
    return {columns: [], serverColumns: [], data: [], loading: true};
  },
  componentDidMount: function() {
    (this.props.provider.bind(this))("init");
  },
  sort: function(col, ascending) {
    this.setState({loading: true});
    (this.props.provider.bind(this))("sort", [col, ascending]);
  },
  render: function() {
    var rows = this.state.data.map(function(rowData, idx) {
      return (
        React.createElement("tr", {key: idx}, 
        
          rowData.map(function(e, idx2) {
            if (typeof e === "boolean") {
              e = e? "yes": "no";
            }
            return React.createElement("td", {key: idx2}, e); 
          })
        
        )
      );
    });

    if (this.state.loading || (rows.length === 0)) {
      var className = this.state.loading? "table-loading": "table-no-results";
      // Display a "no results" message.
      rows = (
        React.createElement("tr", {className: className}, React.createElement("td", {colSpan: this.state.columns.length}, 
          "No results"
        ))
      );
    }

    return (
      React.createElement("div", null, 
        React.createElement("p", {className: "caption"}, 
          this.props.children
        ), 
        React.createElement("table", null, 
          React.createElement(GenericTableHead, {columns: this.state.columns, 
           serverColumns: this.state.serverColumns, dataSort: this.sort}), 
          React.createElement("tbody", null, 
            rows
          )
        )
      )
    );
  }
});

var GenericTableHead = React.createClass({displayName: "GenericTableHead",
  getInitialState: function() {
    return {sortCol: null, sortAscending: null};
  },
  sort: function(idx) {
    var nextState = {sortCol: idx};
    if (idx === this.state.sortCol) {
      // Toggle the sort direction.
      nextState.sortAscending = !(this.state.sortAscending);
    }
    else {
      // Use ascending sort by default.
      nextState.sortAscending = true;
    }

    // Call the parent sort.
    this.props.dataSort(
      this.props.serverColumns[nextState.sortCol],
      nextState.sortAscending
    );
    this.setState(nextState);
  },
  render: function() {
    var columns = this.props.columns.map(function(col, idx) {
      var click = this.sort.bind(this, idx);

      var arrow;
      arrow = this.state.sortAscending? "\u25BC": "\u25B2";
      if (this.state.sortAscending === null) {
        arrow = "";
      }

      if (this.state.sortCol === idx) {
        return (
          React.createElement("th", {key: idx, onClick: click}, 
            col, " ", React.createElement("span", {className: "caret"}, arrow)
          )
        );
      }
      return (
        React.createElement("th", {key: idx, onClick: click}, 
          col, " ", React.createElement("span", {className: "caret"})
        )
      );

    }.bind(this));
    return (
      React.createElement("thead", null, 
        React.createElement("tr", null, 
          columns
        )
      )
    );
  }
});
