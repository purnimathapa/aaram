// Cart page: submit the quantity form as soon as the shopper picks a new
// number, so they do not need a separate Update button. Without this script
// the noscript Update button submits the same form.
(function () {
  "use strict";

  var selects = document.querySelectorAll(".cart-qty-select");
  selects.forEach(function (select) {
    select.addEventListener("change", function () {
      select.form.submit();
    });
  });
})();
