// Product page: update price, stock and the delivery estimate as the shopper
// changes size, thickness or province. The page already works without this
// script (the form reloads with ?size=&thickness=); this just avoids reloads.
(function () {
  "use strict";

  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) {
      return null;
    }
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return null;
    }
  }

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

  function setUpVariantPicker() {
    var form = document.getElementById("variant-form");
    var variants = readJson("variant-data");
    if (!form || !variants) {
      return;
    }

    var priceEl = document.getElementById("variant-price");
    var lineEl = document.getElementById("variant-line");
    var statusEl = document.getElementById("variant-status");
    var coreEl = document.getElementById("illustration-core");

    function currentKey() {
      var size = form.querySelector('input[name="size"]:checked');
      var thickness = form.querySelector('input[name="thickness"]:checked');
      if (!size || !thickness) {
        return null;
      }
      return size.value + "-" + thickness.value;
    }

    function update() {
      var data = variants[currentKey()];
      var thickness = form.querySelector('input[name="thickness"]:checked');
      if (coreEl && thickness) {
        coreEl.style.height = "calc(" + thickness.value + " * 9px)";
      }
      if (!data) {
        // No such size and thickness combination is sold.
        if (statusEl) {
          statusEl.textContent = "Not available";
          statusEl.className = "stock-pill stock-bad";
        }
        return;
      }
      if (priceEl) {
        priceEl.textContent = rupees(data.price);
      }
      if (lineEl) {
        lineEl.textContent = data.variant_line;
      }
      if (statusEl) {
        statusEl.textContent = data.status_text;
        statusEl.className = "stock-pill stock-" + data.status_modifier;
      }
    }

    form.addEventListener("change", update);
    update();
  }

  function setUpDeliveryBox() {
    var box = document.querySelector("[data-provinces]");
    var provinces = readJson("province-data");
    if (!box || !provinces) {
      return;
    }
    var select = document.getElementById("delivery-province");
    var chargeEl = document.getElementById("delivery-charge");
    var daysEl = document.getElementById("delivery-days");
    if (!select) {
      return;
    }
    select.addEventListener("change", function () {
      var data = provinces[select.value];
      if (!data) {
        return;
      }
      if (chargeEl) {
        chargeEl.textContent = rupees(data.charge);
      }
      if (daysEl) {
        daysEl.textContent = data.days;
      }
    });
  }

  setUpVariantPicker();
  setUpDeliveryBox();
})();
