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

forward.variableHist = function(node, variable, transformed) {
  console.log(variable);
  $.ajax({
    url: "variables/plots/histogram.json",
    dataType: "json",
    data: {
      "name": variable,
      "bins": 50
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
      "fill_color": ["black"],
      "line_color": ["white"],
      "alpha": 1.0
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
    console.log(spec);

    var xaxis = {
      "type": "auto",
      "location": "below",
      "grid": true
    };

    var yaxis = {
      "type": "auto",
      "location": "left",
      "grid": true
    };

    var options = {
      title: null,
      min_border: 10,
      plot_width: 800,
      plot_height: 300,
      x_range: [
        Math.min.apply(null, plot_data["left"]),
        Math.max.apply(null, plot_data["right"])
      ],
      y_range: [0, Math.max.apply(null, plot_data["top"])]
    };

    Bokeh.$("#" + node.id).bokeh("figure", {
      options: options,
      glyphs: [spec],
      guides: [xaxis, yaxis]
    })

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

  fig = document.createElement("div");
  forward._figures[name] = fig
  fig.id = name;
  document.getElementById("figures").appendChild(fig);
  return fig;
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
