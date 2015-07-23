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
  render: function() {
      return (
        <tr>
          <td>{this.props.name}</td><td>{this.props.mean.toFixed(3)}</td>
          <td>{this.props.std.toFixed(3)}</td><td>{this.props.nmissing}</td>
          <td>{this.props.transformation ? this.props.transformation: "none"}</td>
          <td>{this.props.covariate}</td>
          <td><a href="">icon</a></td>
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
      <table>
        <thead>
          {thead}
        </thead>
        <tbody>
          {nodes}
        </tbody>
      </table>
    );
  }
});
