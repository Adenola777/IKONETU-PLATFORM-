// The admin pages' small behaviours, as the admin design's boards had them. Each page works without
// this file: the filters have a Show button, and the server checks every confirmation again.
(function () {
  "use strict";

  // On a phone the sidebar's sections start closed behind the Menu button.
  var menu = document.querySelector("[data-menu]");
  if (menu && window.matchMedia("(max-width: 699px)").matches) menu.open = false;

  // A filter form applies a choice as soon as it changes, as the boards' filters did.
  document.querySelectorAll("form[data-auto]").forEach(function (form) {
    var apply = form.querySelector("[data-apply]");
    if (apply) apply.hidden = true;
    form.addEventListener("change", function (e) {
      if (e.target.matches("select, input[type=checkbox], input[type=date]")) form.requestSubmit();
    });
    form.querySelectorAll("input[type=search]").forEach(function (input) {
      var wait;
      input.addEventListener("input", function () {
        clearTimeout(wait);
        wait = setTimeout(function () { form.requestSubmit(); }, 500);
      });
    });
  });

  // A search that submitted keeps the cursor in its box.
  var focused = document.querySelector("form[data-auto] input[type=search]");
  if (focused && focused.value && document.activeElement === document.body) {
    focused.focus();
    focused.setSelectionRange(focused.value.length, focused.value.length);
  }

  // Delete permanently waits until DELETE is typed.
  document.querySelectorAll("form[data-confirm-word]").forEach(function (form) {
    var word = form.getAttribute("data-confirm-word");
    var input = form.querySelector("input[name=confirm]");
    var button = form.querySelector("button[type=submit]");
    function check() { button.disabled = input.value.trim() !== word; }
    input.addEventListener("input", check);
    check();
  });

  // Approve video waits until all four checks are ticked, and says how many are.
  document.querySelectorAll("form[data-all-checks]").forEach(function (form) {
    var boxes = form.querySelectorAll("input[type=checkbox]");
    var button = form.querySelector("button[data-needs-checks]");
    var hint = form.querySelector("[data-checks-hint]");
    function check() {
      var ticked = 0;
      boxes.forEach(function (b) { if (b.checked) ticked += 1; });
      var all = ticked === boxes.length;
      button.disabled = !all;
      if (hint) hint.textContent = all ? "All four are named." : ticked + " of " + boxes.length + " ticked. Tick all four to approve.";
    }
    boxes.forEach(function (b) { b.addEventListener("change", check); });
    check();
  });
})();
