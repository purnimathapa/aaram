// Checkout page: when the customer picks a different address, update the
// delivery charge and total in the summary, and block ordering to a province
// we do not serve. The page still works without this script: the server uses
// the chosen address and recalculates everything when the order is placed.
(function () {
  "use strict";

  var form = document.querySelector("[data-checkout]");
  var dataEl = document.getElementById("address-data");
  if (!form || !dataEl) {
    return;
  }

  var addresses;
  try {
    addresses = JSON.parse(dataEl.textContent);
  } catch (err) {
    return;
  }

  var summary = document.querySelector(".checkout-summary");
  var deliveryEl = document.getElementById("summary-delivery");
  var totalEl = document.getElementById("summary-total");
  var placeButton = form.querySelector(".checkout-place");
  var subtotal = parseInt(summary.getAttribute("data-subtotal"), 10) || 0;

  function groupNepali(digits) {
    if (digits.length <= 3) {
      return digits;
    }
    var lastThree = digits.slice(-3);
    var rest = digits.slice(0, -3);
    var pairs = [];
    while (rest.length > 2) {
      pairs.unshift(rest.slice(-2));
      rest = rest.slice(0, -2);
    }
    pairs.unshift(rest);
    return pairs.join(",") + "," + lastThree;
  }

  function rupees(amount) {
    return "Rs. " + groupNepali(String(amount));
  }

  function update() {
    var checked = form.querySelector('input[name="address"]:checked');
    var data = checked ? addresses[checked.value] : null;
    if (!data) {
      return;
    }
    deliveryEl.textContent = rupees(data.charge);
    totalEl.textContent = rupees(subtotal + data.charge);
    // Do not let the customer order to a province we cannot deliver to.
    placeButton.disabled = !data.serviceable;
  }

  form.addEventListener("change", update);
  update();
})();
