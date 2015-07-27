$(document).ready(function() {

  React.render(
    <VariantTable>
      <strong>Table { forward.Table("variant").number }. </strong>
      information on the analyzed variants.
    </VariantTable>,
    document.getElementById("variant-table")
  );

  React.render(
    <VariableTable type="discrete">
      <strong>Table { forward.Table("discrete-variables").number }. </strong>
      Description of the discrete variables analyzed in this experiment.
    </VariableTable>,
    document.getElementById("discrete-variables-table")
  );

  React.render(
    <VariableTable type="continuous">
      <strong>Table { forward.Table("continuous-variables").number }. </strong>
      Description of the continous variables analyzed in this experiment.   
    </VariableTable>,
    document.getElementById("continuous-variables-table")
  );

});
