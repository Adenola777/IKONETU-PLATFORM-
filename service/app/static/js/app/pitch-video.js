// Switches on captions for each pitch video. The server makes the cues from the transcript and puts
// them in the video's data-cues attribute; they are added through the browser's text track
// interface, so no caption file is fetched. Ported from components/app/pitch-video.tsx.
(function () {
  if (typeof VTTCue === "undefined") return;
  var videos = document.querySelectorAll("video[data-cues]");
  for (var i = 0; i < videos.length; i++) {
    var video = videos[i];
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
