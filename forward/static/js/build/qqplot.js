var createQQ = function(config, data, mountNodeId) {
  var radius = 1.3;

  var translate = function(x, y) {
    return "translate(" + x + ", " + y + ")";
  };

  var margin = {
    "top": 30, "right": 30, "bottom": 50, "left": 50
  };

  var width = config.width - margin.left - margin.right,
      height = config.height - margin.top - margin.bottom;

  var svg = d3.select("#" + mountNodeId).append("svg")
    .attr("width", config.width)
    .attr("height", config.height)
    .append("g")
    .attr("transform", translate(margin.left, margin.top))

  var scaleBuff = 0.2;
  var xScale = d3.scale.linear().domain([
    d3.min(data, function(d) { return d.expected; }) - scaleBuff,
    d3.max(data, function(d) { return d.expected; }) + scaleBuff,
  ]).range([0, width]);

  var yScale = d3.scale.linear().domain([
    d3.min(data, function(d) { return d.observed; }) - scaleBuff,
    d3.max(data, function(d) { return d.observed; }) + scaleBuff,
  ]).range([height, 0]);

  basicAxes([xScale, yScale], ["Expected", "Observed"], svg, width, height);

  var area = d3.svg.area()
    .x(function(d) { return xScale(d.expected); })
    .y0(function(d) { return yScale(d.ci[0]); })
    .y1(function(d) { return yScale(d.ci[1]); });

  svg.append("path").datum(data).attr("d", area)
    .attr("opacity", 0.08);

  var color = d3.scale.category20();
  var scatter = svg.append("g");
  scatter.selectAll(".qqpoint").data(data).enter()
    .append("circle")
    .attr("class", function(d) { return "qqpoint pk" + d.pk; })
    .attr("cx", function(d) { return xScale(d.expected); })
    .attr("cy", function(d) { return yScale(d.observed); })
    .attr("r", radius)
    .attr("fill", function(d) {
      return config.phenotypeScale(d.phenotype);   
    });

  var tooltip;
  var showTooltip = function(d) {
    if (tooltip) {
      tooltip.close();
      tooltip = undefined;
    }
    var point = d3.selectAll(".qqpoint.pk" + d.pk)[0][0];
    var point_data = d3.selectAll(".mhpoint.pk" + d.pk)[0][0].__data__;

    var effect = {"label": "Effect", "value": point_data.effect};
    if (config.modelType == "linear") {
      effect.label = "&beta;";
    }
    else if (config.modelType == "logistic") {
      effect.label = "OR";
    }

    tooltip = forward.Tooltip(
      point,
      ("<p><em>Phenotype:</em> " + point_data.outcome + "</p>" +
       "<p><em>Variant:</em> " + point_data.variant + "</p>" +
       "<p><em>p-value:</em> " + forward.formatPValue(point_data.p) + "</p>" +
       "<p><em>" + effect.label + ":</em> " + d3.format(".3f")(effect.value) + "</p>"),
      -1 * (radius + 1),
      -1
    );
  };

  var removeTooltip = function() {
    if (tooltip) tooltip.close();
    tooltip = undefined;
  };

  var voronoi = d3.geom.voronoi()
    .x(function(d) { return xScale(d.expected); })
    .y(function(d) { return yScale(d.observed); })
    .clipExtent([[0, 0], [width, height]]);
  scatter.selectAll("path")
    .data(voronoi(data))
    .enter().append("path")
    .attr("d", function(d, i) { return "M" + d.join("L") + "Z"; })
    .datum(function(d) { return d.point; })
    .attr("class", function(d) { return "voronoi " + d.pk; })
    .style("stroke", "none")  // Color me to show grid.
    .style("stroke-opacity", 0.5)
    .style("fill", "none")
    .style("pointer-events", "all")
    .on("mouseover", showTooltip)

  svg.on("mouseout", removeTooltip);

};

var basicAxes = function(scales, labels, node, width, height) {
  var xAxis = d3.svg.axis().scale(scales[0]).orient("bottom");
  var yAxis = d3.svg.axis().scale(scales[1]).orient("left");

  node.append("g")
    .attr("class", "xAxis axis")
    .attr("transform", "translate(0," + height + ")").call(xAxis);

  node.append("g")
    .attr("class", "yAxis axis")
    .call(yAxis);

  var xAxisLabel = node.append("text")
    .attr("class", "label xAxisLabel")
    .attr("x", width / 2)
    .attr("y", height + 35)
    .attr("text-anchor", "middle")
    .text(labels[0]);

  var yAxisLabel = node.append("text")
    .attr("class", "label yAxisLabel")
    .attr(
      "transform",
      "translate(-30, " + height/2 + ")" + "rotate(-90)"
    )
    .attr("text-anchor", "middle")
    .text(labels[1]);
};
