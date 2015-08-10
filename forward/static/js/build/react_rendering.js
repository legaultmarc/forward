$(document).ready(function() {

  React.render(
    React.createElement(VariantTable, null, 
      React.createElement("strong", null, "Table ",  forward.Table("variant").number, ". "), 
      "information on the analyzed variants."
    ),
    document.getElementById("variant-table")
  );

  React.render(
    React.createElement(VariableTable, {type: "discrete"}, 
      React.createElement("strong", null, "Table ",  forward.Table("discrete-variables").number, ". "), 
      "Description of the discrete variables analyzed in this experiment."
    ),
    document.getElementById("discrete-variables-table")
  );

  React.render(
    React.createElement(VariableTable, {type: "continuous"}, 
      React.createElement("strong", null, "Table ",  forward.Table("continuous-variables").number, ". "), 
      "Description of the continous variables analyzed in this experiment."   
    ),
    document.getElementById("continuous-variables-table")
  );

  (function () {
    var correlationPlot = forward.Figure("correlationPlot");
    forward.phenotypeCorrelationPlot({
      "figure": correlationPlot,
      "width": 500,
      "height": 500,
      "margins": {"top": 30, "right": 30, "bottom": 30, "left": 30}
    });
  })();

});
