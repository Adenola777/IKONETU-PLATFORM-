// The reviewer's decision form. Approving asks how the evidence was checked and what was compared; asking for
// more or rejecting asks for a reason the founder reads. Choosing a decision swaps the fields, drawn as they
// first appeared, from the form's templates. Ported from app/admin/evidence/[id]/decision-form.tsx.
(function () {
  var form = document.querySelector("form[data-decision-form]");
  if (!form) return;
  var approve = form.querySelector('template[data-branch="approve"]');
  var reason = form.querySelector('template[data-branch="reason"]');
  var current = (form.querySelector('input[name="decision"]:checked') || {}).value || "approve";

  // The fields the server drew sit between the decision fieldset and the templates.
  var shown = [];
  for (var node = form.querySelector("fieldset").nextElementSibling; node && node.tagName !== "TEMPLATE"; node = node.nextElementSibling) {
    shown.push(node);
  }

  function draw(decision) {
    var approving = decision === "approve";
    if (approving !== (current === "approve")) {
      shown.forEach(function (n) { n.remove(); });
      var fresh = (approving ? approve : reason).content.cloneNode(true);
      shown = Array.prototype.slice.call(fresh.children);
      form.insertBefore(fresh, approve);
    }
    current = decision;
    var label = form.querySelector('label[for="d-reason"]');
    if (!approving && label) {
      label.textContent = (decision === "reject" ? "Why is it not accepted?" : "What more do you need?") + " The founder reads this.";
    }
  }

  form.addEventListener("change", function (event) {
    if (event.target.name === "decision") draw(event.target.value);
  });
})();
