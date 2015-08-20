$(document).ready(function() {

  React.render(
    React.createElement(GenericTable, {provider: forward.variantProvider}, 
      React.createElement("strong", null, "Table ",  forward.Table("variant").number, ". "), 
      "information on the analyzed variants."
    ),
    document.getElementById("variant-table")
  );

  React.render(
    React.createElement(GenericTable, {provider: forward.discreteVariablesProvider}, 
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

  // Related phenotypes exclusions.
  React.render(
    React.createElement(ExclusionTable, null, 
      React.createElement("strong", null, "Table ",  forward.Table("related-exclusions").number, ". "), 
      "Summary of the sample exclusions (from controls) based on phenotype" + ' ' +
      "correlation."
    ),
    document.getElementById("related-exclusions-table")
  );

  // Correlation plot.
  (function () {
    var correlationPlot = forward.Figure("correlationPlot");
    forward.phenotypeCorrelationPlot({
      "figure": correlationPlot,
      "width": 500,
      "height": 500
    });
  })();

});
