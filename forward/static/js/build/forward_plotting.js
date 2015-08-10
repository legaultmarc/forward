forward.variableNormalQQ = function(config) {
  $.ajax({
    url: "variables/plots/normalqq.json",
    dataType: "json",
    data: {
      "name": config.variable,
      "transformation": config.transformation? config.transformation: null
    },
    success: function(data) {
      plot(data)
    },
    error: function(error) {
      console.log("Query for histogram information failed.");
    }
  });

  var plot = function(data) {
    var plot_data = {
      "expected": data.expected,
      "observed": data.observed,
      "fill_color": [config.fillColor || "black"],
      "line_color": [config.lineColor || "black"],
      "alpha": config.alpha || 1.0
    };

    var xaxis = {
      "type": "auto",
      "location": "below",
      "grid": true,
      "axis_label": config.xLabel || null,
      "axis_label_text_font_size": "9pt"
    };

    var yaxis = {
      "type": "auto",
      "location": "left",
      "grid": true,
      "axis_label": config.yLabel || null,
      "axis_label_text_font_size": "9pt"
    };

    var options = {
      "title": null,
      "min_border": 10,
      "plot_width": config["width"] || 700,
      "plot_height": config["height"] || 250,
      "x_range": [data.xLimits[0], data.xLimits[1]],
      "y_range": [data.yLimits[0], data.yLimits[1]],
    };

    var spec = {
      "type": "Circle",
      "source": plot_data,
      "x": "expected",
      "y": "observed",
      "radius": 0.001 * (data.xLimits[1] - data.xLimits[0]),
      "fill_color": "fill_color",
      "line_color": "line_color",
      "alpha": "alpha"
    };

    var _line = {
      "_x": [data.xLimits[0], data.xLimits[1]],
      "_y": [
        data.m * data.xLimits[0] + data.b,
        data.m * data.xLimits[1] + data.b,
      ]
    };
    var line = {
      "type": "Line",
      "source": _line,
      "x": "_x",
      "y": "_y",
      "line_color": "#555555",
      "line_dash": [5, 2]
    };

    Bokeh.$("#" + config.figure.id).bokeh("figure", {
      "options": options,
      "glyphs": [spec, line],
      "guides": [xaxis, yaxis],
      "tools": ["Pan", "WheelZoom"]
    })

    // Adjust the parent div so it has the same width.
    config.figure.style.width = (options.plot_width + 20) + "px";
    config.figure.style.margin = "0 auto";
  }

};

forward.variableHist = function(config) {
  $.ajax({
    url: "variables/plots/histogram.json",
    dataType: "json",
    data: {
      "name": config.variable,
      "bins": config.bins || 50,
      "transformation": config.transformation? config.transformation: null
    },
    success: function(data) {
      plot(data)
    },
    error: function(error) {
      console.log("Query for histogram information failed.");
    }
  });

  var plot = function(data) {
    var plot_data = {
      "top": data["hist"],
      "bottom": forward.valuesLike(data["hist"]),
      "left": data["edges"].slice(0, data["edges"].length - 1),
      "right": data["edges"].slice(1, data["edges"].length),
      "fill_color": [config.fillColor || "black"],
      "line_color": [config.lineColor || "white"],
      "alpha": config.alpha || 1.0
    };

    var spec = {
      "type": "Quad",
      "source": plot_data,
      "right": "right",
      "left": "left",
      "bottom": "bottom",
      "top": "top",
      "fill_color": "fill_color",
      "line_color": "line_color",
      "alpha": "alpha"
    };

    var xaxis = {
      "type": "auto",
      "location": "below",
      "grid": true,
      "axis_label": config.xLabel || null,
      "axis_label_text_font_size": "9pt"
    };

    var yaxis = {
      "type": "auto",
      "location": "left",
      "grid": true,
      "axis_label": config.yLabel || null,
      "axis_label_text_font_size": "9pt"
    };

    var maxY = Math.max.apply(null, plot_data["top"]);
    var options = {
      "title": null,
      "min_border": 10,
      "plot_width": config.width || 700,
      "plot_height": config.height || 250,
      "x_range": [
        Math.min.apply(null, plot_data["left"]),
        Math.max.apply(null, plot_data["right"])
      ],
      "y_range": [0, maxY + 0.05 * maxY],
    };

    Bokeh.$("#" + config.figure.id).bokeh("figure", {
      options: options,
      glyphs: [spec],
      guides: [xaxis, yaxis]
    })

    // Adjust the parent div so it has the same width.
    config.figure.style.width = (options.plot_width + 20) + "px";
    config.figure.style.margin = "0 auto";

  }
}

forward.phenotypeCorrelationPlot = function(config) {

  $.ajax({
    url: "variables/plots/correlation_plot.json",
    dataType: "json",
    success: function(data) {
      plot(config, data)
    },
    error: function(error) {
      console.log("Query for corrplot failed.");
    }
  });

  var plot = function(config, data) {
    
    // Preprocessing.
    var n = data.names.length;
    for (var i = 0; i < n; i++) {
      for (var j = 0; j < n; j++) {
        data.data[i][j] = {
          "x": i, "y": j, "val": data.data[i][j]
        };
        if (i < j) { data.data[i][j].val = -10; }
      }
    }

    // Setting up colormap.
    // Because correlation is in [-1, 1], we will map these colors from blue
    // to red (with 0 = white).
    var color = d3.scale.linear()
      .domain([-1, 0, 1])
      .range(["#3687FF", "#F5F8FF", "#FF5F4C"]);

    // Create the wrapping svg element.
    var svg = d3.select(config.figure).append("svg")
      .attr("width", config.width + config.margins.left + config.margins.right)
      .attr(
        "height",
        config.height + config.margins.top + config.margins.bottom
      )
      .attr("class", "corrplot")
      .append("g")
      .attr("style", "plot-wrap")
      .attr(
        "transform",
        "translate(" + config.margins.left + "," + config.margins.top + ")"
      );

    // Create the axis (phenotype labels).
    var labelLength = 150;  // This is how much space we leave for labels.
    var cellHeight = (config.height - labelLength) / n;

    var yLabels = svg.selectAll(".ylabel")
      .data(data.names)
      .enter().append("text")
      .text(function (d) { return d; })
      .attr("x", 0)
      .attr("y", function (d, i) { return i * cellHeight; })
      .style("text-anchor", "end")
      .attr(
        "transform",
        "translate(" + (labelLength - 10) + ", " + (0.5 * cellHeight + 5) + ")"
      )
      .attr("class", "label ylabel");

    var xLabels = svg.selectAll(".xlabel")
      .data(data.names)
      .enter().append("text")
      .text(function (d) { return d; })
      .attr("transform", function(d, i) {
          var x = i * cellHeight + labelLength + 0.5 * cellHeight + 5;
          var y = n * cellHeight + 15;
          return "translate(" + x + ", " + y + ")rotate(-45)";
      })
      .style("text-anchor", "end")
      .attr("class", "label xlabel");

    // Draw the actual correlation plot.
    var rows = svg.selectAll("g")
      .data(data.data)
      .enter().append("g")
      .attr("transform",
        function(_, idx) {
          return "translate(0, " + idx * cellHeight + ")";
        }
      )
      .selectAll(".box")  // The cells.
      .data(function(row) { return row; })
      .enter().append("rect")
      .attr("x", function(row, idx) {
          return idx * cellHeight + labelLength;
      })
      .attr("y", "0")
      .attr("rx", "4") // Rounded corners radius.
      .attr("ry", "4")
      .attr("class", "box")
      .style("fill", "#EEEEEE")  // Initial color (will be transitioned).
      .attr("height", cellHeight)
      .attr("width", cellHeight)
      .on("mouseover", function(p) {
        var d = d3.select(this).datum();

        if (d.x < d.y) { return; }  // Only interact with the bottom part.

        d3.select(this).transition().duration(300)
          .style("fill", "#000000")
          .style("opacity", "0.8");

        // Update the info field wrt the selection.
        info.select(".desc").text(
          data.names[d.x] + " - " + data.names[d.y]
        );

        info.select(".value").text(
          "Correlation: " + d3.format(".3f")(d.val)
        );

      })
      .on("mouseout", function() {
        d3.select(this).transition().duration(200)
          .style("fill", function(d) {
            if (d.val == -10) return "#FFFFFF";
            return color(d.val);
          })
          .style("opacity", "1")

        info.select(".desc").text("");
        info.select(".value").text("");

      })
      .transition()
        .duration(1000)
        .style("fill", function(d) {
          if (d.val == -10) return "#FFFFFF";
          return color(d.val);
        });

    // The info text shows up in the top right corner and displays information
    // about the cell the user is hovering.
    var info = svg.append("text")
      .attr("x", 270)
      .attr("y", 22)
      .attr("class", "info")

    info.append("tspan").attr("class", "desc")
    info.append("tspan").attr("class", "value")
      .attr("dy", "1.5em").attr("x", 270)


  } // End plot.

}
