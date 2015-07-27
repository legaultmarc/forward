forward = {};

// TODO. We could use caching.
forward.withVariants = function(f) {
  $.getJSON("variants.json", function(data) {
    f(data);
  });
};

forward.withVariables = function(f) {
  $.getJSON("variables.json", function(data) {
    f(data);
  });
};

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
      "bottom": forward.zerosLike(data["hist"]),
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

/**
 * Create a figure object.
 **/
forward.Figure = function(name) {
  if (forward._figures === undefined) {
    forward._figures = {}  // Hash of name to dom element.
  }

  var fig = forward._figures[name]
  if (fig) {
    return fig;
  }

  // Create the DOM element.
  fig = document.createElement("div");
  forward._figures[name] = fig
  fig.id = name;

  // Create a 'x' that removes this div.
  var closeButton = document.createElement("a");
  closeButton.innerHTML = "&times;";
  closeButton.className = "close-figure";

  fig.appendChild(closeButton);

  document.getElementById("figures").appendChild(fig);

  closeButton.addEventListener("click", function() {
    delete forward._figures[fig.id];
    document.getElementById("figures").removeChild(fig);
  });

  return fig;
};

/**
 * Create a table object.
 **/
forward.Table = function(name) {
  // TODO implement me.
  that = {};

  if (forward._tables === undefined) {
    forward._tables = {}  // Hash of name to dom element.
  }

  that.number = 3;
  return that;
};

/**
 * Checks if a figure with the provided name already exists.
 **/
forward.figureExists = function(name) {
  if (forward._figures === undefined) return false;
  return forward._figures.hasOwnProperty(name);
};

forward.zerosLike = function(li) {
  var out = new Array(li.length);
  for (var i = 0; i < li.length; i++) {
    out[i] = 0;
  }
  return out;
};
