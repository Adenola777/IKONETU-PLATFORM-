// The founder's evidence form. Choosing what the evidence shows puts that signal's "what to send" sentence under
// the list, and a self-declared signal hides the file and link fields, because a statement takes neither. The
// server applies the same rule, so the form works without this script.
(function () {
  var form = document.querySelector("form[data-evidence-form]");
  if (!form) return;
  var select = form.querySelector('select[name="signal"]');
  var hint = form.querySelector("[data-signal-hint]");
  var proof = form.querySelectorAll("[data-proof]");
  var statementNote = form.querySelector("[data-statement-note]");

  function draw() {
    var option = select.options[select.selectedIndex];
    var text = option && option.getAttribute("data-hint");
    var statement = option && option.getAttribute("data-how") === "self";
    hint.textContent = text ? "What to send: " + text.charAt(0).toLowerCase() + text.slice(1) : "";
    hint.hidden = !text;
    proof.forEach(function (n) { n.hidden = statement; });
    statementNote.hidden = !statement;
  }

  select.addEventListener("change", draw);
  draw();
})();
