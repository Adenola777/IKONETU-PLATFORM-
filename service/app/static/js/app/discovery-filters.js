// The discovery filters. Without script they are a form that sends a GET request. With script each change
// applies at once: the page for the new address is fetched, its results replace these, and focus stays on
// the box that changed. On narrow screens the filters fold away behind a button, so the results come first.
// Ported from app/investor/filters.tsx.
(function () {
  var form = document.getElementById("disc-filters");
  var toggle = document.querySelector("button.ftoggle");
  if (!form || !toggle) return;
  var open = false;

  function chosen() {
    var n = 0;
    var data = new FormData(form);
    data.forEach(function (v) { if (typeof v === "string" && v) n++; });
    return n;
  }
  function label() {
    var n = chosen();
    toggle.textContent = open ? "Hide filters" : n ? "Filters (" + n + " chosen)" : "Filters";
  }

  toggle.addEventListener("click", function () {
    open = !open;
    toggle.setAttribute("aria-expanded", String(open));
    form.classList.toggle("open", open);
    label();
  });

  var latest = 0;
  form.addEventListener("change", async function () {
    var q = new URLSearchParams();
    new FormData(form).forEach(function (v, k) { if (typeof v === "string" && v) q.append(k, v); });
    var s = q.toString();
    var address = s ? "/investor?" + s : "/investor";
    var mine = ++latest;
    // The boxes now drawn ticked are the page's own state, as they would be if the page had loaded at this address.
    var boxes = form.querySelectorAll("input");
    for (var i = 0; i < boxes.length; i++) boxes[i].defaultChecked = boxes[i].checked;
    history.replaceState(history.state, "", address);
    label();
    try {
      var response = await fetch(address, { credentials: "same-origin", headers: { Accept: "text/html" } });
      if (!response.ok || response.redirected) throw new Error("refused");
      var page = new DOMParser().parseFromString(await response.text(), "text/html");
      if (mine !== latest) return;
      var fresh = page.querySelector('section[aria-labelledby="res-h"]');
      var here = document.querySelector('section[aria-labelledby="res-h"]');
      if (!fresh || !here) throw new Error("no results");
      here.replaceWith(fresh);
      if (window.IK && window.IK.bindThumbs) window.IK.bindThumbs(fresh);
    } catch (e) {
      window.location.assign(address);
    }
  });
})();
