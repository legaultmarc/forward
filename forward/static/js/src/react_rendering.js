$(document).ready(function() {

  var variantTable = document.getElementById("variant-table");
  forward.xrefs.register(variantTable, "table");
  React.render(
    <GenericTable provider={forward.variantProvider}>
      <a name="variant-table"></a>
      <strong>Table {forward.xrefs.getJSXXref("variant-table")}. </strong>
      information on the analyzed variants.
    </GenericTable>,
    variantTable
  );

  var discreteVarTable = document.getElementById("discrete-variables-table");
  forward.xrefs.register(discreteVarTable, "table");
  React.render(
    <GenericTable provider={forward.discreteVariablesProvider}>
      <strong>Table {forward.xrefs.getJSXXref("discrete-variables-table")}. </strong>
      Description of the discrete variables analyzed in this experiment.
    </GenericTable>,
    discreteVarTable
  );

  var contVarTable = document.getElementById("continuous-variables-table");
  forward.xrefs.register(contVarTable, "table");
  React.render(
    <ContinuousVariableTable>
      <strong>Table {forward.xrefs.getJSXXref("continuous-variables-table")}. </strong>
      Description of the continous variables analyzed in this experiment.   
    </ContinuousVariableTable>,
    contVarTable
  );

  // Related phenotypes exclusions.
  var relatedExclusionsTable = document.getElementById("related-exclusions-table");
  forward.xrefs.register(relatedExclusionsTable, "table");
  React.render(
    <GenericTable provider={forward.exclusionProvider}>
      <strong>Table {forward.xrefs.getJSXXref("related-exclusions-table")}. </strong>
      Summary of the sample exclusions (from controls) based on phenotype
      correlation.
    </GenericTable>,
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
