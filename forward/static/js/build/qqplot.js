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
  var xScale = d3.scale.linear().domain(
    data["bounds_expected"]
  ).range([0, width]);

  var yScale = d3.scale.linear().domain([
    data["bounds_observed"][0] - scaleBuff,
    data["bounds_observed"][1] + scaleBuff,
  ]).range([height, 0]);

  var rankTransform = function(rank) {
    return xScale(-1 * Math.log10(rank / n));
  };

  basicAxes([xScale, yScale], ["Expected", "Observed"], svg, width, height);

  var n = data.n;
  var area = d3.svg.area()
    .x(function(d, i) { return rankTransform(i + 1); })
    .y0(function(d) { return yScale(d[0]); })
    .y1(function(d) { return yScale(d[1]); })

  svg.append("path").datum(data.ci).attr("d", area)
    .attr("opacity", 0.1);

  var color = d3.scale.category20();
  var line = d3.svg.line()
    .x(function(d, i) { return rankTransform(i + 1); })
    .y(function(d) { return yScale(d); })

  var linePlots = svg.selectAll(".outcome-group").data(data.outcomes).enter()
    .append("g")
    .attr("class", function(d) { return "outcome-group group-" + d; })

  linePlots.append("path")
    .datum(function(d) { return data["lines"][d]; })
    .attr("d", line)
    .attr("fill", "none")
    .attr("stroke", function(d) { return color(d); })

  var voronoi = d3.geom.voronoi()
    .x(function(d) { return xScale(d.expected); })
    .y(function(d) { return yScale(d.observed); })

  var voronoiGroup = svg.append("g");

  // Select the points that diverge for the voronoi.
  // This reduces the computational burden for the voronoi.
  var voronoiData = [];
  for (var phen in data.lines) {
    for (var i = 0; i < data.lines[phen].length; i++) {
      var observed = data.lines[phen][i];
      var expected = -1 * Math.log10((i + 1) / n);

      if (!(data.ci[i][0] < observed && observed < data.ci[i][1])) {
        // Add points outside of the CI to the Voronoi.
        voronoiData.push({
          "observed": observed,
          "expected": expected,
          "phenotype": phen
        });
      }
    }
  }

  voronoiData = voronoi(voronoiData);

  var tooltip;
  var voronoiPath = svg.selectAll("path.voronoi").data(voronoiData)
    .enter().append("path")
    .attr("d", function(d) {
      // Ignore invalid polygons.
      for (var i = 0; i < d.length; i++) {
        for (var j = 0; j < d[i].length; j++) {
          if (d[i][j] === undefined || isNaN(d[i][j])) {
            return;
          }
        }
      }
      return "M" + d.join("L") + "Z";
    })
    .attr("stroke", "none")
    .attr("fill", "none")
    .style("pointer-events", "all")
    .on("mouseover", function(d) {
      svg.select(".group-" + d.point.phenotype)
        .classed({"group-selected": true})

      tooltip = forward.Tooltip(
        $("#" + mountNodeId + " svg").get()[0],
        ("<p><em>Outcome</em>: " + d.point.phenotype + "</p>" +
         "<p><em>Expected</em>: " + d3.format(".3f")(d.point.expected) + "</p>" +
         "<p><em>Observed</em>: " + d3.format(".3f")(d.point.observed) + "</p>"),
        xScale(d.point.expected) + margin.left,
        yScale(d.point.observed) + margin.top
      );
    })
    .on("mouseout", function() {
      if (tooltip) tooltip.close();
      svg.selectAll(".group-selected").classed({"group-selected": false}) ;
    });

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
