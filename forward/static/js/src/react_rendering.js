$(document).ready(function() {

  React.render(
    <VariantTable />,
    document.getElementById("variant-table")
  );

  React.render(
    <VariableTable type="discrete" />,
    document.getElementById("discrete-variables-table")
  );

  React.render(
    <VariableTable type="continuous" />,
    document.getElementById("continuous-variables-table")
  );

});
