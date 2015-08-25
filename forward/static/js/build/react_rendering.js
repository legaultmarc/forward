$(document).ready(function() {

  var variantTable = document.getElementById("variant-table");
  forward.xrefs.register(variantTable, "table");
  React.render(
    React.createElement(GenericTable, {provider: forward.variantProvider}, 
      React.createElement("a", {name: "variant-table"}), 
      React.createElement("strong", null, "Table ", forward.xrefs.getJSXXref("variant-table"), ". "), 
      "information on the analyzed variants."
    ),
    variantTable
  );

  var discreteVarTable = document.getElementById("discrete-variables-table");
  forward.xrefs.register(discreteVarTable, "table");
  React.render(
    React.createElement(GenericTable, {provider: forward.discreteVariablesProvider}, 
      React.createElement("strong", null, "Table ", forward.xrefs.getJSXXref("discrete-variables-table"), ". "), 
      "Description of the discrete variables analyzed in this experiment."
    ),
    discreteVarTable
  );

  var contVarTable = document.getElementById("continuous-variables-table");
  forward.xrefs.register(contVarTable, "table");
  React.render(
    React.createElement(ContinuousVariableTable, null, 
      React.createElement("strong", null, "Table ", forward.xrefs.getJSXXref("continuous-variables-table"), ". "), 
      "Description of the continous variables analyzed in this experiment."   
    ),
    contVarTable
  );

  // Related phenotypes exclusions.
  var relatedExclusionsTable = document.getElementById("related-exclusions-table");
  forward.xrefs.register(relatedExclusionsTable, "table");
  React.render(
    React.createElement(GenericTable, {provider: forward.exclusionProvider}, 
      React.createElement("strong", null, "Table ", forward.xrefs.getJSXXref("related-exclusions-table"), ". "), 
      "Summary of the sample exclusions (from controls) based on phenotype" + ' ' +
      "correlation."
    ),
    relatedExclusionsTable
  );

  // Correlation plot.
  (function () {
    var correlationPlot = forward.xrefs.create("figure", "correlation-plot");

    correlationPlot.innerHTML += (
      "<p class='caption'><strong>Figure " +
      forward.xrefs.getXref("correlation-plot") +
      ".</strong> Correlation plot showing pairwise correlation coefficients " +
      "for the different outcomes. Red and blue indicate positive and negative " + 
      "coefficients, respectively.</p>"
    );

    document.getElementById("figures").appendChild(correlationPlot);
    forward.phenotypeCorrelationPlot({
      "figure": correlationPlot,
      "width": 500,
      "height": 500
    });
  })();

  forward.xrefs.reNumber();

});
