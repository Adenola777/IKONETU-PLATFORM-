// Keeps the activity feed live. Every 30 seconds while the page is in view, and whenever the person
// comes back to it, it asks /activity/new for the entries made since the newest one shown and adds
// them at the top. The server draws each entry, so it looks the same as the ones on the page.
// The answer is HTML the server drew with every value escaped, read into a template element, which
// runs no script. Without the script the page still works, and a reload shows what is new. It stops
// when an answer does not come from the feed, as happens when the session has ended and the server
// asks the person to sign in again.
(function () {
  var list = document.querySelector("[data-activity]");
  if (!list || !window.fetch || !("content" in document.createElement("template"))) return;
  var empty = document.querySelector("[data-activity-empty]");
  var live = document.getElementById("act-live");
  var newest = list.getAttribute("data-newest");
  var busy = false;
  var stopped = false;

  function add(html) {
    var holder = document.createElement("template");
    holder.innerHTML = html;
    var items = holder.content.querySelectorAll("li[data-id]");
    var added = 0;
    for (var i = items.length - 1; i >= 0; i--) {
      if (list.querySelector('li[data-id="' + items[i].getAttribute("data-id") + '"]')) continue;
      list.insertBefore(items[i], list.firstChild);
      added++;
    }
    if (!added) return;
    list.hidden = false;
    if (empty) empty.hidden = true;
    if (live) live.textContent = added === 1 ? "1 new entry at the top of the feed." : added + " new entries at the top of the feed.";
  }

  function check() {
    if (busy || stopped || document.visibilityState !== "visible") return;
    busy = true;
    fetch("/activity/new?after=" + encodeURIComponent(newest), {
      credentials: "same-origin",
      headers: { Accept: "text/html" },
      redirect: "manual",
    })
      .then(function (response) {
        if (!response.headers.get("X-Activity-Feed")) {
          stopped = true;
          return null;
        }
        if (response.status !== 200) return null;
        newest = response.headers.get("X-Activity-Newest") || newest;
        return response.text().then(add);
      })
      .catch(function () {})
      .then(function () { busy = false; });
  }

  setInterval(check, 30000);
  document.addEventListener("visibilitychange", check);
})();
