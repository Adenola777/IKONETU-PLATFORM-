// Draws the sign-in code as six boxes over the one real input, as the app flow design shows it. The
// input stays the field that is typed into, pasted into and filled by the phone, and it is sent as it
// is, so the page works the same without this script, where the input shows as one wide box.
(function () {
  var wrap = document.querySelector("[data-code-boxes]");
  if (!wrap) return;
  var input = wrap.querySelector("input");
  if (!input) return;
  var row = document.createElement("div");
  row.className = "cb-row";
  row.setAttribute("aria-hidden", "true");
  for (var i = 0; i < 6; i++) row.appendChild(document.createElement("span"));
  wrap.appendChild(row);
  wrap.classList.add("cb-on");
  function draw() {
    var digits = input.value.replace(/\D/g, "").slice(0, 6);
    var focused = document.activeElement === input;
    for (var i = 0; i < 6; i++) {
      var box = row.children[i];
      box.textContent = digits.charAt(i);
      // The box the next digit goes in is marked while the input has focus.
      box.className = (digits.charAt(i) ? "full" : "") + (focused && i === Math.min(digits.length, 5) ? " next" : "");
    }
  }
  ["input", "change", "focus", "blur"].forEach(function (name) { input.addEventListener(name, draw); });
  draw();
})();
