var createQQ = function(config, data, mountNodeId) {
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

  var scatter = svg.append("g");
  scatter.selectAll(".point").data(data).enter()
    .append("circle")
    .attr("class", "point")
    .attr("cx", function(d) { return xScale(d.expected); })
    .attr("cy", function(d) { return yScale(d.observed); })
    .attr("r", 1)
    .attr("fill", "#555555")

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
