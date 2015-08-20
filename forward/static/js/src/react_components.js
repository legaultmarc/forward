// Variant Table
var VariantRow = React.createClass({
  render: function() {
    return (
      <tr><td><a name={this.props.name}></a>{this.props.name}</td>
          <td>{this.props.chrom}</td>
          <td>{this.props.pos}</td><td>{this.props.minor}</td>
          <td>{this.props.major}</td><td>{Math.round(this.props.mac)}</td>
          <td>{(0.5 * this.props.mac / this.props.n_non_missing).toFixed(3)}</td>
          <td>{this.props.n_missing}</td><td>{this.props.n_non_missing}</td></tr>
    );
  }
});

var VariantTable = React.createClass({
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
        <VariantRow key={idx} name={v.name} chrom={v.chrom} pos={v.pos}
         mac={v.mac} minor={v.minor} major={v.major} n_missing={v.n_missing}
         n_non_missing={v.n_non_missing} />
      );
    });
    return (
     <div>
       <p className="caption">{this.props.children}</p>
       <table>
          <thead>
            <tr>
              <th>name</th>
              <th>chrom</th>
              <th>pos</th>
              <th>minor</th>
              <th>major</th>
              <th>mac</th>
              <th>maf</th>
              <th><em>n</em> missing</th>
              <th><em>n</em> non missing</th>
            </tr>
          </thead>
          <tbody>
            {variantNodes}
          </tbody>
       </table>
     </div>
    );
  }
});

var ExclusionRow = React.createClass({
  render: function() {
    var relatedList = this.props.related.join(", ");
    return (
      <tr><td>{this.props.phenotype}</td><td>{relatedList}</td>
          <td>{this.props.n_excluded}</td></tr>
    );
  }
});

var ExclusionTable = React.createClass({
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
        <ExclusionRow key={idx} phenotype={o.phenotype} related={o.related}
         n_excluded={o.n_excluded} />
      );
    });
    return (
      <div>
        <p className="caption">{this.props.children}</p>
        <table>
          <thead>
            <tr>
              <th>Phenotype</th>
              <th>Related phenotypes</th>
              <th>
                n excluded (threshold: <span className="fwdinfo phenotype_correlation_for_exclusion"></span>)
              </th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </div>
    );
  }
});

// Variables Table
var ContinuousVariableRow = React.createClass({
  buildModal: function() {

    document.getElementById("variable-modal").innerHTML = "";
    var modal = React.render(
      <Modal title={this.props.name}>
        <ContinuousVariablePlotForm name={this.props.name}
         transformation={this.props.transformation} />
      </Modal>,
      document.getElementById("variable-modal")
    );
    modal.show();

  },
  render: function() {
      return (
        <tr>
          <td>{this.props.name}</td><td>{this.props.mean.toFixed(3)}</td>
          <td>{this.props.std.toFixed(3)}</td><td>{this.props.nmissing}</td>
          <td>{this.props.transformation ? this.props.transformation: "none"}</td>
          <td>{this.props.covariate}</td>
          <td>
            <a className="button" role="button" onClick={this.buildModal}>generate plot</a>
          </td>
        </tr>
      )
  }
});

var DiscreteVariableRow = React.createClass({
  render: function() {
      return (
        <tr>
          <td>{this.props.name}</td><td>{this.props.ncontrols}</td>
          <td>{this.props.ncases}</td><td>{this.props.nmissing}</td>
          <td>{this.props.covariate}</td>
        </tr>
      );
  }
});

var VariableTable = React.createClass({
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
            <DiscreteVariableRow key={i} name={v.name} ncontrols={v.n_controls}
             nmissing={v.n_missing} ncases={v.n_cases}
             covariate={v.is_covariate ? "yes": "no"} />
          )
        }
        else if (v.variable_type === "continuous") {
          nodes.push(
            <ContinuousVariableRow key={i} name={v.name} std={v.std}
             mean={v.mean} covariate={v.is_covariate ? "yes": "no"}
             transformation={v.transformation} nmissing={v.n_missing} />
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
        <tr>
          <th>Name</th>
          <th>n controls</th>
          <th>n cases</th>
          <th>n missing</th>
          <th>covariate</th>
        </tr>
      );
    }
    else if (this.props.type === "continuous") {
      thead = (
        <tr>
          <th>Name</th>
          <th>Mean</th>
          <th>Std</th>
          <th>n missing</th>
          <th>transformation</th>
          <th>covariate</th>
          <th>plots</th>
        </tr>
      );
    }
    else {
      throw "ValueError: Invalid prop variable type " + this.props.type;
    }

    return (
      <div>
        <p className="caption">{ this.props.children }</p>
        <table>
          <thead>
            {thead}
          </thead>
          <tbody>
            {nodes}
          </tbody>
        </table>
      </div>
    );
  }
});

var ContinuousVariablePlotForm = React.createClass({
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
        <fieldset>
          <legend>Plots for transformed variables</legend>
          <input type="checkbox" name="plots" value="histt" id="histt" ref="histt" />
          <label htmlFor="histt">Histogram (transformed)</label>

          <input type="checkbox" name="plots" value="QQt" id="QQt" ref="QQt" />
          <label htmlFor="QQt">Normal QQ plot (transformed)</label>
        </fieldset>
      );
    }
    return (
      <form onSubmit={this.handleSubmit} className="plot-form">
        <fieldset>
          <legend>Plot types</legend>
          <input type="checkbox" name="plots" value="hist" id="hist" ref="hist" />
          <label htmlFor="hist">Histogram</label>

          <input type="checkbox" name="plots" value="QQ" id="QQ" ref="QQ" />
          <label htmlFor="QQ">Normal QQ plot</label>
        </fieldset>
        { transformed_form_elements }
        <input type="submit" value="Generate plots" className="button" />
      </form>
    );
  }
});

// Modal box.
var Modal = React.createClass({
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
      <div className="modal-wrapper"
           style={{"display": this.state.visible ? "block": "none"}}>
        <div className="modal-overlay"></div>
        <div className="modal">
          <a role="button" onClick={this.hide} className="close">&times;</a>
          <h2>{this.props.title}</h2>
          {this.props.children}
        </div>
      </div>
    );
  }
});

// Generic table
var GenericTable = React.createClass({
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
        <tr key={idx}>
        {
          rowData.map(function(e, idx2) {
            if (typeof e === "boolean") {
              e = e? "yes": "no";
            }
            return <td key={idx2}>{e}</td>; 
          })
        }
        </tr>
      );
    });

    if (this.state.loading || (rows.length === 0)) {
      var className = this.state.loading? "table-loading": "table-no-results";
      // Display a "no results" message.
      rows = (
        <tr className={className}><td colSpan={this.state.columns.length}>
          No results
        </td></tr>
      );
    }

    return (
      <div>
        {this.props.children}
        <table>
          <GenericTableHead columns={this.state.columns}
           serverColumns={this.state.serverColumns} dataSort={this.sort} />
          <tbody>
            {rows}
          </tbody>
        </table>
      </div>
    );
  }
});

var GenericTableHead = React.createClass({
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
          <th key={idx} onClick={click}>
            {col} <span className="caret">{arrow}</span>
          </th>
        );
      }
      return (
        <th key={idx} onClick={click}>
          {col} <span className="caret"></span>
        </th>
      );

    }.bind(this));
    return (
      <thead>
        <tr>
          {columns}
        </tr>
      </thead>
    );
  }
});
