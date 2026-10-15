"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/site/icons";
import { cuesFromTranscript } from "@/lib/captions";

const PREVIEW_SECONDS = 5;

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

/**
 * A pitch thumbnail in the search results. Pointing at it plays a muted
 * preview of five seconds with captions, as the For investors page says. It
 * never plays under reduced motion. Selecting it opens the founder profile,
 * where the full pitch plays with sound, captions and the transcript.
 */
export function PreviewThumb({ href, src, transcript, duration, label, length }: {
  href: string; src: string | null; transcript: string; duration: number; label: string; length: string;
}) {
  const video = useRef<HTMLVideoElement | null>(null);
  const [caption, setCaption] = useState("");
  const [playing, setPlaying] = useState(false);
  const cues = useRef(cuesFromTranscript(transcript, duration));

  useEffect(() => {
    cues.current = cuesFromTranscript(transcript, duration);
  }, [transcript, duration]);

  const stop = () => {
    const v = video.current;
    if (v) {
      v.pause();
      v.currentTime = 0;
    }
    setPlaying(false);
    setCaption("");
  };

  const start = () => {
    const v = video.current;
    if (!v || !src || reducedMotion()) return;
    v.currentTime = 0;
    v.muted = true;
    void v.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  };

  const tick = () => {
    const v = video.current;
    if (!v) return;
    if (v.currentTime >= PREVIEW_SECONDS) return stop();
    setCaption(cues.current.find((c) => v.currentTime >= c.start && v.currentTime < c.end)?.text ?? "");
  };

  return (
    <Link href={href} className="thumb" aria-label={label} onMouseEnter={start} onMouseLeave={stop}>
      {src && <video ref={video} src={src} muted playsInline preload="none" onTimeUpdate={tick} aria-hidden="true" tabIndex={-1} />}
      {!playing && <span className="playdot" aria-hidden="true"><Icon name="play" size={16} fill /></span>}
      {length && <span className="len" aria-hidden="true">{length}</span>}
      {playing && (
        <span className="pv" aria-hidden="true">
          <span className="pvlbl"><Icon name="volume-x" size={12} />Muted preview</span>
          {caption && <span className="pvcap">{caption}</span>}
        </span>
      )}
    </Link>
  );
}
