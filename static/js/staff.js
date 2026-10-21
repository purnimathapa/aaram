// Staff pages: submit a filter form as soon as a select changes, so there is
// no separate Apply button to click. Each such select is marked
// data-autosubmit; without this script the noscript Apply button still works.
(function () {
  "use strict";

  var selects = document.querySelectorAll("select[data-autosubmit]");
  selects.forEach(function (select) {
    select.addEventListener("change", function () {
      select.form.submit();
    });
  });
})();
