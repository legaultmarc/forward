// Variant Table
var VariantRow = React.createClass({displayName: "VariantRow",
  render: function() {
    return (
      React.createElement("tr", null, React.createElement("td", null, React.createElement("a", {name: this.props.name}), this.props.name), 
          React.createElement("td", null, this.props.chrom), 
          React.createElement("td", null, this.props.pos), React.createElement("td", null, this.props.minor), 
          React.createElement("td", null, this.props.major), React.createElement("td", null, Math.round(this.props.mac)), 
          React.createElement("td", null, (0.5 * this.props.mac / this.props.n_non_missing).toFixed(3)), 
          React.createElement("td", null, this.props.n_missing), React.createElement("td", null, this.props.n_non_missing))
    );
  }
});

var VariantTable = React.createClass({displayName: "VariantTable",
  getInitialState: function() {
    return {data: []};
  },
  componentDidMount: function() {
    forward.withVariants(function(variants) {
      this.setState({data: variants})
    }.bind(this));
  },
  render: function() {
    var variantNodes = this.state.data.map(function(v, idx) {
      return (
        React.createElement(VariantRow, {key: idx, name: v.name, chrom: v.chrom, pos: v.pos, 
         mac: v.mac, minor: v.minor, major: v.major, n_missing: v.n_missing, 
         n_non_missing: v.n_non_missing})
      );
    });
    return (
     React.createElement("div", null, 
       React.createElement("p", {className: "caption"}, this.props.children), 
       React.createElement("table", null, 
          React.createElement("thead", null, 
            React.createElement("tr", null, 
              React.createElement("th", null, "name"), 
              React.createElement("th", null, "chrom"), 
              React.createElement("th", null, "pos"), 
              React.createElement("th", null, "minor"), 
              React.createElement("th", null, "major"), 
              React.createElement("th", null, "mac"), 
              React.createElement("th", null, "maf"), 
              React.createElement("th", null, React.createElement("em", null, "n"), " missing"), 
              React.createElement("th", null, React.createElement("em", null, "n"), " non missing")
            )
          ), 
          React.createElement("tbody", null, 
            variantNodes
          )
       )
     )
    );
  }
});

var ExclusionRow = React.createClass({displayName: "ExclusionRow",
  render: function() {
    var relatedList = this.props.related.join(", ");
    return (
      React.createElement("tr", null, React.createElement("td", null, this.props.phenotype), React.createElement("td", null, relatedList), 
          React.createElement("td", null, this.props.n_excluded))
    );
  }
});

var ExclusionTable = React.createClass({displayName: "ExclusionTable",
  getInitialState: function() {
    return {exclusions: [], threshold: null};
  },
  componentDidMount: function() {
    forward.withExclusions(function(data) {
      this.setState({exclusions: data});
    }.bind(this));
  },
  render: function() {
    var rows = this.state.exclusions.map(function(o, idx) {
      return (
        React.createElement(ExclusionRow, {key: idx, phenotype: o.phenotype, related: o.related, 
         n_excluded: o.n_excluded})
      );
    });
    return (
      React.createElement("div", null, 
        React.createElement("p", {className: "caption"}, this.props.children), 
        React.createElement("table", null, 
          React.createElement("thead", null, 
            React.createElement("tr", null, 
              React.createElement("th", null, "Phenotype"), 
              React.createElement("th", null, "Related phenotypes"), 
              React.createElement("th", null, 
                "n excluded (threshold: ", React.createElement("span", {className: "fwdinfo phenotype_correlation_for_exclusion"}), ")"
              )
            )
          ), 
          React.createElement("tbody", null, 
            rows
          )
        )
      )
    );
  }
});

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

var DiscreteVariableRow = React.createClass({displayName: "DiscreteVariableRow",
  render: function() {
      return (
        React.createElement("tr", null, 
          React.createElement("td", null, this.props.name), React.createElement("td", null, this.props.ncontrols), 
          React.createElement("td", null, this.props.ncases), React.createElement("td", null, this.props.nmissing), 
          React.createElement("td", null, this.props.covariate)
        )
      );
  }
});

var VariableTable = React.createClass({displayName: "VariableTable",
  getInitialState: function() {
    return {data: []};
  },
  componentDidMount: function() {
    forward.withVariables(function(data) {
      this.setState({"data": data})
    }.bind(this));
  },
  render: function() {
    var nodes = []
    var data = this.state.data
    for (var i = 0; i < data.length; i++) {
      var v = data[i]
      if (v.variable_type === this.props.type) {
        if (v.variable_type === "discrete") {
          nodes.push(
            React.createElement(DiscreteVariableRow, {key: i, name: v.name, ncontrols: v.n_controls, 
             nmissing: v.n_missing, ncases: v.n_cases, 
             covariate: v.is_covariate ? "yes": "no"})
          )
        }
        else if (v.variable_type === "continuous") {
          nodes.push(
            React.createElement(ContinuousVariableRow, {key: i, name: v.name, std: v.std, 
             mean: v.mean, covariate: v.is_covariate ? "yes": "no", 
             transformation: v.transformation, nmissing: v.n_missing})
          )
        }
        else {
          throw "ValueError: Unknown variable type " + v.variable_type;
        }
      }
    }

    var thead;
    if (this.props.type === "discrete") {
      thead = (
        React.createElement("tr", null, 
          React.createElement("th", null, "Name"), 
          React.createElement("th", null, "n controls"), 
          React.createElement("th", null, "n cases"), 
          React.createElement("th", null, "n missing"), 
          React.createElement("th", null, "covariate")
        )
      );
    }
    else if (this.props.type === "continuous") {
      thead = (
        React.createElement("tr", null, 
          React.createElement("th", null, "Name"), 
          React.createElement("th", null, "Mean"), 
          React.createElement("th", null, "Std"), 
          React.createElement("th", null, "n missing"), 
          React.createElement("th", null, "transformation"), 
          React.createElement("th", null, "covariate"), 
          React.createElement("th", null, "plots")
        )
      );
    }
    else {
      throw "ValueError: Invalid prop variable type " + this.props.type;
    }

    return (
      React.createElement("div", null, 
        React.createElement("p", {className: "caption"},  this.props.children), 
        React.createElement("table", null, 
          React.createElement("thead", null, 
            thead
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

// Generic components, refactor.

var GenericTable = React.createClass({displayName: "GenericTable",
  getInitialState: function() {
    return {columns: [], serverColumns: [], data: []};
  },
  componentDidMount: function() {
    (forward.discreteVariablesProvider.bind(this))("init");
  },
  sort: function(col, ascending) {
    (forward.discreteVariablesProvider.bind(this))("sort", [col, ascending]);
  },
  render: function() {
    var rows = this.state.data.map(function(rowData, idx) {
      return (
        React.createElement("tr", {key: idx}, 
        rowData.map(function(e, idx2) { return React.createElement("td", {key: idx2}, e); })
        )
      );
    });

    return (
      React.createElement("div", null, 
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
      arrow = this.state.sortAscending? "\u2193": "\u2191";
      if (this.state.sortAscending === null) {
        arrow = "";
      }

      if (this.state.sortCol === idx) {
        return React.createElement("th", {key: idx, onClick: click}, col + " " + arrow);
      }
      return React.createElement("th", {key: idx, onClick: click}, col);

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
