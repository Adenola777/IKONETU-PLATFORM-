// A pitch thumbnail in the search results. Pointing at it plays a muted preview of five seconds with
// captions, as the For investors page says. It never plays under reduced motion. Selecting it opens the
// founder profile, where the full pitch plays with sound, captions and the transcript. The server puts
// the caption cues in the thumbnail's data-cues attribute. Ported from components/app/preview-thumb.tsx.
(function () {
  var PREVIEW_SECONDS = 5;

  function reducedMotion() {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) {
      return false;
    }
  }

  function bind(thumb) {
    if (thumb.dataset.bound) return;
    thumb.dataset.bound = "yes";
    var video = thumb.querySelector("video");
    var dot = thumb.querySelector(".playdot");
    var cues = [];
    try {
      cues = JSON.parse(thumb.dataset.cues || "[]");
    } catch (e) {
      cues = [];
    }
    var shown = null;

    function setPlaying(playing) {
      if (playing && !shown) {
        if (dot) dot.remove();
        shown = document.createElement("span");
        shown.className = "pv";
        shown.setAttribute("aria-hidden", "true");
        var label = document.getElementById("pv-label");
        if (label) shown.appendChild(label.content.cloneNode(true));
        thumb.appendChild(shown);
      } else if (!playing && shown) {
        shown.remove();
        shown = null;
        if (dot) thumb.insertBefore(dot, thumb.querySelector(".len"));
      }
    }
    function setCaption(text) {
      if (!shown) return;
      var cap = shown.querySelector(".pvcap");
      if (!text) {
        if (cap) cap.remove();
        return;
      }
      if (!cap) {
        cap = document.createElement("span");
        cap.className = "pvcap";
        shown.appendChild(cap);
      }
      cap.textContent = text;
    }
    function stop() {
      if (video) {
        video.pause();
        video.currentTime = 0;
      }
      setPlaying(false);
    }

    thumb.addEventListener("mouseenter", function () {
      if (!video || reducedMotion()) return;
      video.currentTime = 0;
      video.muted = true;
      video.play().then(function () { setPlaying(true); }, function () { setPlaying(false); });
    });
    thumb.addEventListener("mouseleave", stop);
    if (video) {
      video.addEventListener("timeupdate", function () {
        if (video.currentTime >= PREVIEW_SECONDS) return stop();
        var t = video.currentTime;
        var cue = cues.find(function (c) { return t >= c.start && t < c.end; });
        setCaption(cue ? cue.text : "");
      });
    }
  }

  window.IK = window.IK || {};
  window.IK.bindThumbs = function (root) {
    var thumbs = (root || document).querySelectorAll("a.thumb");
    for (var i = 0; i < thumbs.length; i++) bind(thumbs[i]);
  };
  window.IK.bindThumbs(document);
})();
