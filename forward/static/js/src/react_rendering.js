$(document).ready(function() {

  React.render(
    <GenericTable provider={forward.variantProvider}>
      <strong>Table { forward.Table("variant").number }. </strong>
      information on the analyzed variants.
    </GenericTable>,
    document.getElementById("variant-table")
  );

  React.render(
    <GenericTable provider={forward.discreteVariablesProvider}>
      <strong>Table { forward.Table("discrete-variables").number }. </strong>
      Description of the discrete variables analyzed in this experiment.
    </GenericTable>,
    document.getElementById("discrete-variables-table")
  );

  React.render(
    <ContinuousVariableTable>
      <strong>Table { forward.Table("continuous-variables").number }. </strong>
      Description of the continous variables analyzed in this experiment.   
    </ContinuousVariableTable>,
    document.getElementById("continuous-variables-table")
  );

  // Related phenotypes exclusions.
  React.render(
    <ExclusionTable>
      <strong>Table { forward.Table("related-exclusions").number }. </strong>
      Summary of the sample exclusions (from controls) based on phenotype
      correlation.
    </ExclusionTable>,
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
