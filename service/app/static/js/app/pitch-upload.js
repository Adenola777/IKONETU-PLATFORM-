// The founder chooses a video and types what they say. The video goes from the browser straight to
// the founder's own folder in storage, as supabase-js sent it, and the server then records it with
// the transcript. Ported from app/dashboard/pitch/upload.tsx.
(function () {
  var form = document.querySelector("form[data-pitch-upload]");
  if (!form) return;
  var TYPES = { "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov" };
  var MAX_BYTES = 50 * 1024 * 1024;
  var MAX_SECONDS = 90;
  var input = document.getElementById("p-video");
  var text = document.getElementById("p-transcript");
  var button = form.querySelector('button[type="submit"]');
  var label = button.textContent;
  var file = null;
  var preview = "";
  var duration = 0;

  // A video's length, read in the browser before anything is uploaded.
  function readDuration(url) {
    return new Promise(function (resolve) {
      var v = document.createElement("video");
      v.preload = "metadata";
      v.onloadedmetadata = function () { resolve(isFinite(v.duration) ? v.duration : 0); };
      v.onerror = function () { resolve(0); };
      v.src = url;
    });
  }

  // The error under a field, tied to it by id, as the other forms show it.
  function fieldError(field, name, hint, message) {
    var old = document.getElementById(name + "-err");
    if (old) old.remove();
    if (message) {
      var p = document.createElement("p");
      p.id = name + "-err";
      p.className = "err";
      p.textContent = message;
      field.closest(".field").appendChild(p);
      field.setAttribute("aria-invalid", "true");
      field.setAttribute("aria-describedby", name + "-err");
    } else {
      field.removeAttribute("aria-invalid");
      field.setAttribute("aria-describedby", hint);
    }
  }
  function setErrors(errors) {
    fieldError(input, "video", "p-video-hint", errors.video);
    fieldError(text, "transcript", "p-transcript-hint", errors.transcript);
  }
  function setMessage(ok, message) {
    var old = form.querySelector(":scope > .status");
    if (old) old.remove();
    if (!message) return;
    var p = document.createElement("p");
    p.className = "status " + (ok ? "status-ok" : "status-err");
    p.setAttribute("role", ok ? "status" : "alert");
    p.textContent = message;
    form.insertBefore(p, form.firstChild);
  }
  function setPreview(url) {
    var old = form.querySelector(".player");
    if (old) old.remove();
    if (preview) URL.revokeObjectURL(preview);
    preview = url;
    if (!url) return;
    var box = document.createElement("div");
    box.className = "player";
    box.style.maxWidth = "560px";
    var video = document.createElement("video");
    video.src = url;
    video.controls = true;
    video.playsInline = true;
    video.setAttribute("aria-label", "Preview of the video you chose");
    box.appendChild(video);
    input.closest(".field").after(box);
  }
  function setBusy(busy) {
    button.disabled = busy;
    button.textContent = busy ? "Uploading…" : label;
  }

  input.addEventListener("change", async function () {
    setMessage(true, "");
    var f = input.files && input.files[0];
    setPreview("");
    file = null;
    duration = 0;
    if (!f) return;
    if (!TYPES[f.type]) return setErrors({ video: "Choose an MP4, WebM or MOV video." });
    if (f.size > MAX_BYTES) return setErrors({ video: "The video must be 50 MB or smaller. Record at 720p, or shorten it." });
    var url = URL.createObjectURL(f);
    var seconds = await readDuration(url);
    if (!seconds) {
      URL.revokeObjectURL(url);
      return setErrors({ video: "This browser cannot read this video. Export it as an MP4 (H.264) file, or try another browser." });
    }
    if (seconds > MAX_SECONDS) {
      URL.revokeObjectURL(url);
      return setErrors({ video: "This video is " + Math.round(seconds) + " seconds long. Keep the pitch to 90 seconds or less." });
    }
    setErrors({});
    file = f;
    duration = seconds;
    setPreview(url);
  });

  async function post(url, body) {
    var response = await fetch(url, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
      credentials: "same-origin",
    });
    if (!response.ok || !(response.headers.get("content-type") || "").includes("application/json")) throw new Error("refused");
    return response.json();
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    setMessage(true, "");
    var words = text.value.trim();
    var errors = {};
    if (!file) errors.video = "Choose your pitch video.";
    if (words.length < 20) errors.transcript = "Type what you say in the pitch, in at least 20 characters.";
    setErrors(errors);
    if (errors.video || errors.transcript) return;

    var storage = form.dataset.storage;
    if (!storage || !form.dataset.key) return setMessage(false, "Uploads are not open yet. Please try again soon.");
    setBusy(true);
    var path = form.dataset.user + "/" + crypto.randomUUID() + "." + TYPES[file.type];
    try {
      var token = (await post("/dashboard/pitch/token")).token;
      var body = new FormData();
      body.append("cacheControl", "3600");
      body.append("", file);
      var up = await fetch(storage + "/storage/v1/object/pitches/" + path, {
        method: "POST",
        headers: { apikey: form.dataset.key, Authorization: "Bearer " + token, "x-upsert": "false" },
        body: body,
      });
      if (!up.ok) throw new Error("upload");
    } catch (e) {
      setBusy(false);
      return setMessage(false, "The upload did not finish. Check your connection and try again.");
    }
    var saved;
    try {
      saved = await post("/dashboard/pitch/record", { path: path, mimeType: file.type, size: file.size, duration: duration, transcript: words });
    } catch (e) {
      saved = { status: "error", message: "We could not save your pitch. Please try again." };
    }
    setBusy(false);
    if (saved.status === "error") return setMessage(false, saved.message);
    setMessage(true, saved.message);
    file = null;
    // The server set a one-time confirmation, which the page shows when it loads again.
    window.location.assign(window.location.pathname);
  });
})();
