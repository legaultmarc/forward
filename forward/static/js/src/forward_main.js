forward = {};

// TODO. We could use caching.
forward.withVariants = function(f) {
  $.getJSON(window.location.pathname + "/variants.json", function(data) {
    f(data);
  });
};

forward.withVariables = function(f) {
  $.getJSON(window.location.pathname + "/variables.json", function(data) {
    f(data);
  });
};


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

forward.valuesLike = function(li, value) {
  if (value === undefined) value = 0;
  var out = new Array(li.length);
  for (var i = 0; i < li.length; i++) {
    out[i] = value;
  }
  return out;
};

forward.range = function(n) {
  return Array.apply(null, Array(n)).map(function(_, i) { return i; });
};

/**
 * Elementwise or vector addition.
 **/
forward.add = function(array, elem) {
  // If it's an array, we do element wise.
  if ($.isArray(elem)) {
    return array.map(function(e, i) {
      return e + elem[i];
    });
  }
  else {
    return array.map(function(e) {
      return e + elem
    });
  }
};

/**
 * Get task handler.
 **/
forward.handleTask = function(taskType, taskName) {
  switch (taskType) {
    case "LogisticTest":
      forward._handleLogistic(taskName);
      break;
    case "LinearTest":
      forward._handleLinear(taskName);
      break;
  }
};

forward._handleLogistic = function(taskName) {
  var node = document.createElement("div");
  node.id = "section_" + taskName;
  document.getElementById("results").appendChild(node);

  $.ajax({
    url: window.location.pathname + "/tasks/logistic_section.html",
    data: {"task": taskName},
    success: function(data) {
      node.innerHTML = data;
      fwdGLM.renderSection(taskName, "logistic");
    }
  });
};

forward._handleLinear = function(taskName) {
  var node = document.createElement("div");
  node.id = "section_" + taskName;
  document.getElementById("results").appendChild(node);

  $.ajax({
    url: window.location.pathname + "/tasks/linear_section.html",
    data: {"task": taskName},
    success: function(data) {
      node.innerHTML = data;
      fwdGLM.renderSection(taskName, "linear");
    }
  });
};
