// The walkthrough video. It never plays by itself and has no sound. Captions are built in script from the
// same cues as the caption file, and show from the start. `openWalk` scrolls to the video and starts it,
// for the hero's "Watch how it works". Ported on 17 October 2026 from apps/web/components/site/walkthrough.ts.
import { WALK_CUES, WALK_LENGTH, WALK_LINES } from "./walk-data.js";

export function walkVals(s, set, ctx) {
  return {
    walkVideoRef: (v) => {
      ctx.walkVideo = v;
      if (!v) return;
      v.controls = true;
      v.playsInline = true;
      try {
        if (!v.ikCaptions && v.addTextTrack && typeof VTTCue !== "undefined") {
          const track = v.addTextTrack("captions", "English", "en");
          for (const [start, end, text] of WALK_CUES) track.addCue(new VTTCue(start, end, text));
          track.mode = "showing";
          v.ikCaptions = track;
        }
      } catch {
        // Without text tracks the transcript still carries every line.
      }
    },
    walkLength: WALK_LENGTH,
    walkLines: WALK_LINES,
    walkTranscriptOpen: s.walkTranscriptOpen,
    toggleWalkTranscript: () => set((now) => ({ ...now, walkTranscriptOpen: !now.walkTranscriptOpen })),
    openWalk: () => {
      const v = ctx.walkVideo;
      if (!v) return;
      try {
        if (v.ikCaptions) v.ikCaptions.mode = "showing";
        const calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        v.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "center" });
        v.focus({ preventScroll: true });
        const playing = v.play();
        if (playing && playing.catch) playing.catch(() => {});
      } catch {
        // If the browser refuses, the video's own Play button still works.
      }
    },
  };
}
