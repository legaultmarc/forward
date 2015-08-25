var manhattan = function(config, data, mountNodeId) {

  var plotComponents = {};
  plotComponents.phenotypeScale = config.phenotypeScale;

  var translate = function(x, y) {
    return "translate(" + x + ", " + y + ")";
  };

  var margin = {
    "top": 10, "right": 30, "bottom": 50, "left": 50
  };

  var width = config.width - margin.left - margin.right,
      height = config.height - margin.top - margin.bottom;

  var svg = d3.select("#" + mountNodeId + " .plot").append("svg")
    .attr("width", config.width)
    .attr("height", config.height)
    .append("g")
    .attr("transform", translate(margin.left, margin.top))
  plotComponents.svg = svg;

  // Create the scales for both axes.
  var xScale = d3.scale.linear().domain([
      d3.min(data, function(d) { return d.position; }) - 500,
      d3.max(data, function(d) { return d.position; }) + 500,
  ]).range([0, width]);
  plotComponents.xScale = xScale;

  var yScale = d3.scale.linear()
    .domain([
      0,
      Math.max(
        d3.max(data, function(d) { return -Math.log10(d.p); }) + 1,
        10
      )
    ])
    .range([height, 0])
  plotComponents.yScale = yScale;

  // Draw the axes.
  var xAxis = d3.svg.axis().scale(xScale).orient("bottom");
  svg.append("g")
    .attr("class", "xAxis axis")
    .attr("transform", translate(0, height)).call(xAxis);
  plotComponents.xAxis = xAxis;

  var yAxis = d3.svg.axis().scale(yScale).orient("left").tickSize(-width);
  var gy = svg.append("g")
    .attr("class", "yAxis axis")
    .call(yAxis);
  plotComponents.yAxis = yAxis;

  gy.selectAll("g").filter(function(d) { return d; })
    .classed("minor", true);


  // Add labels.
  var xAxisLabel = svg.append("text")
    .attr("class", "label xAxisLabel")
    .attr("x", width / 2)
    .attr("y", height + 35)
    .attr("text-anchor", "middle")
    .text("Position");
  plotComponents.xAxisLabel = xAxisLabel;

  var yAxisLabel = svg.append("text")
    .attr("class", "label yAxisLabel")
    .attr("transform", translate(-25, height/2) + "rotate(-90)")
    .attr("text-anchor", "middle")
    .text("-log(p)");
  plotComponents.yAxisLabel = yAxisLabel;

  // Create the scatter plot.
  var scatter = svg.append("g").attr("class", "dataPoints")
  var infoBox = infoBoxInit(mountNodeId);

  scatter.selectAll(".point").data(data).enter()
    .append("circle")
    .attr("class", "point")
    .attr("cx", function(d) { return xScale(d.position); })
    .attr("cy", function(d) { return yScale(-1 * Math.log10(d.p)); })
    .attr("r", 3)
    .attr("fill", "#555555")
    .on("mouseover", function(data) {
      this._prev_color = this.getAttribute("fill");
      d3.select(this).transition().duration(200)
        .attr("r", 6)
        .attr("fill", "#000000")
      infoBox(data);
    })
    .on("mouseout", function() {
      d3.select(this).transition().duration(200)
        .attr("r", 3)
        .attr("fill", this._prev_color)

      delete this._prev_color
    })

    bindControls(data, plotComponents, mountNodeId, config.effectLabel);

}

/**
 * Event binding for controls.
 **/
var bindControls = function(data, plotComponents, mountNodeId, effectLabel) {
  var sel = "#" + mountNodeId;

  var _colorByPhen = function() {
    var points = d3.selectAll(sel + " .manhattan .point")
    if (points.classed("colored")) {
      points.transition().duration(800)
        .attr("fill", "#555555")
      points.classed({"colored": false});
    }
    else {
      points.transition().duration(800)
        .attr("fill", function(data) {
          return plotComponents.phenotypeScale(data.outcome);
        })
      points.classed({"colored": true})
    }
  };
  $(sel + " .colorByPhen").click(_colorByPhen);

  var effectScale = d3.scale.linear()
    .domain([-5, 1, 6])
    .range(["#3A92E8", "#DDDDDD", "#FA6052"]).clamp(true);

  var _colorByEffect = function() {
    var points = d3.selectAll(sel + " .manhattan .point")
    if (points.classed("colored")) {
      points.transition().duration(800)
        .attr("fill", "#555555")
      points.classed({"colored": false});
    }
    else {
      points.transition().duration(800)
        .attr("fill", function(data) {
          return effectScale(data.effect);
        })
      points.classed({"colored": true})
    }
  };
  $(sel + " .colorByEffect").click(_colorByEffect);

  var _axisEffect = function() {
    var label = d3.select(sel + " .manhattan .xAxisLabel");

    var x;
    if (label.text() == "Position") {
      x = "effect";
      label.text(effectLabel || "Effect");
    }
    else {
      x = "position";
      label.text("Position");
    }

    plotComponents.xScale.domain([
        d3.min(data, function(d) { return d[x]; }),
        d3.max(data, function(d) { return d[x]; })
    ]);

    d3.select(sel + " .manhattan .xAxis")
      .transition().duration(1500).ease("sin")
      .call(plotComponents.xAxis);

    d3.selectAll(sel + " .manhattan .point").transition().duration(1500)
      .attr("cx", function(d) {
        return plotComponents.xScale(d[x]);
      });

  };
  $(sel + " .axisEffect").click(_axisEffect);
  
};

var infoBoxInit = function(mountNodeId) {
  var box = $("#" + mountNodeId + " .manhattanPlotInformation");
  return function(data) {
    if (!data) {
      box.html("");
      return;
    }
    box.html(
      "<p>" +
      "<em>Phenotype:</em> " + data.outcome + "<br />" +
      "<em>Variant:</em> " + data.variant + "<br />" +
      "<em>p-value:</em> " + d3.format(".4e")(data.p) + "<br />" +
      "<em>Effect size:</em> " + d3.format(".3f")(data.effect) +
      "</p>"
    );
  };
};
