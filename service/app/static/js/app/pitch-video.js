// Switches on captions for each pitch video. The server makes the cues from the transcript and puts
// them in the video's data-cues attribute; they are added through the browser's text track
// interface, so no caption file is fetched. Ported from components/app/pitch-video.tsx.
// A video that cannot be played shows the message pitch_video.html holds for it, and the message
// goes again once the video plays.
(function () {
  var videos = document.querySelectorAll("video[data-cues]");
  for (var i = 0; i < videos.length; i++) {
    var video = videos[i];
    var box = video.closest(".stack-s");
    var message = box && box.querySelector("[data-pitch-error]");
    if (message) {
      video.addEventListener("error", function (m) { return function () { m.hidden = false; }; }(message));
      video.addEventListener("playing", function (m) { return function () { m.hidden = true; }; }(message));
      // The video may have failed before this script ran, since it starts loading as the page is read.
      if (video.error || video.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) message.hidden = false;
    }
    if (typeof VTTCue === "undefined") continue;
    var cues;
    try {
      cues = JSON.parse(video.dataset.cues);
    } catch (e) {
      continue;
    }
    var track = video.addTextTrack("captions", "English", "en");
    for (var j = 0; j < cues.length; j++) track.addCue(new VTTCue(cues[j].start, cues[j].end, cues[j].text));
    track.mode = "showing";
  }
})();
