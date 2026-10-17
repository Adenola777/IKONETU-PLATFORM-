// While a form is being sent, its button shows what is happening ("Sending…") and cannot be pressed
// again, as the Next.js forms did. The label comes from the button's data-pending attribute. Pressing
// the browser's back button returns the page as it was, so the label is put back when a page is shown.
(function () {
  document.addEventListener("submit", function (event) {
    if (event.defaultPrevented) return;
    var form = event.target;
    var buttons = form.querySelectorAll("button[data-pending]");
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (!b.dataset.label) b.dataset.label = b.textContent;
      b.textContent = b.dataset.pending;
      // Disabled after this tick, so the browser still sends the press of the button itself.
      setTimeout(function (button) { button.disabled = true; }, 0, b);
    }
  });
  window.addEventListener("pageshow", function () {
    var buttons = document.querySelectorAll("button[data-pending][data-label]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].textContent = buttons[i].dataset.label;
      buttons[i].disabled = false;
    }
  });
})();
