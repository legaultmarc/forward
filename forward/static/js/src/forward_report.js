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
