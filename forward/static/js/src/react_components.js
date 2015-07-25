// Variant Table
var VariantRow = React.createClass({
  render: function() {
    return (
      <tr><td>{this.props.name}</td><td>{this.props.chrom}</td>
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
    );
  }
});

// Variables Table
var ContinuousVariableRow = React.createClass({
  buildModal: function() {

    document.getElementById("variable-modal").innerHTML = "";
    var modal = React.render(
      <Modal title={this.props.name}>
        <ContinuousVariablePlotForm name={this.props.name} />
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
      this.setState({data: data})
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
          console.log("Unknown variable type " + v.variable_type);
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
      console.log("Invalid prop variable type " + this.props.type);
    }

    return (
      <div>
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

        console.log("Generate the " + node.value + " plot for " + this.props.name);

        switch(node.value) {

          case "hist":
            var transformed = false;
          case "histt":
            var transformed = true;
            var figName = this.props.name + node.value;
            if (forward.figureExists(figName)) {
              break;
            }

            var figure = forward.Figure(figName);
            forward.variableHist(figure, this.props.name, transformed)
            break;
        }
      }
    }

    React.unmountComponentAtNode(document.getElementById("variable-modal"));
    if (figure) figure.scrollIntoView();
  },
  render: function() {
    return (
      <form onSubmit={this.handleSubmit}>
        <fieldset>
          <input type="checkbox" name="plots" value="QQ" id="QQ" ref="QQ" /><label htmlFor="QQ">QQ plot</label>
          <input type="checkbox" name="plots" value="QQt" id="QQt" ref="QQt" /><label htmlFor="QQt">QQ plot (transformed)</label>
        </fieldset>

        <fieldset>
          <input type="checkbox" name="plots" value="hist" id="hist" ref="hist" /><label htmlFor="hist">Histogram</label>
          <input type="checkbox" name="plots" value="histt" id="histt" ref="histt" /><label htmlFor="histt">Histogram (transformed)</label>
        </fieldset>

        <input type="submit" value="Generate plots" />
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
