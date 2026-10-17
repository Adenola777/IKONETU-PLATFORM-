"use client";

import { useEffect, useRef } from "react";
import { cuesFromTranscript } from "@/lib/captions";

/**
 * A founder's pitch, with captions made from the transcript and switched on.
 * The captions are added through the browser's text track interface, so no
 * caption file is fetched. The transcript is shown in full below the video.
 */
export function PitchVideo({ src, transcript, duration, title }: { src: string; transcript: string; duration: number; title: string }) {
  const ref = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video || typeof VTTCue === "undefined") return;
    const track = video.addTextTrack("captions", "English", "en");
    for (const cue of cuesFromTranscript(transcript, duration)) track.addCue(new VTTCue(cue.start, cue.end, cue.text));
    track.mode = "showing";
    return () => {
      track.mode = "disabled";
    };
  }, [transcript, duration]);

  return (
    <div className="stack-s">
      <div className="player">
        <video ref={ref} src={src} controls preload="metadata" playsInline aria-label={title} />
      </div>
      <details className="transcript">
        <summary>Read the transcript</summary>
        <p>{transcript}</p>
      </details>
      <p className="small" style={{ margin: 0 }}>
        The founder typed the transcript. The captions are made from it and timed by the length of each sentence, so they may run a
        little ahead of or behind the speech.
      </p>
    </div>
  );
}
