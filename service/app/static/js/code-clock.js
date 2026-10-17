// Counts down the life of the sign-in code once a second. The server writes the first value,
// so the page reads correctly before this runs or without it.
(function () {
  var hint = document.querySelector("[data-expires-at]");
  if (!hint) return;
  var expiresAt = Number(hint.dataset.expiresAt);
  function tick() {
    var left = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    var clock = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
    hint.textContent = left > 0 ? "The code expires in " + clock + "." : "The code has expired. Ask for a new one below.";
  }
  tick();
  setInterval(tick, 1000);
})();
