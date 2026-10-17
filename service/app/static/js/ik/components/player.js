// The pitch player dialog. Ported on 17 October 2026 from apps/web/components/site/pitch-player.tsx.
// Other components open it through ctx.registry.player.open(id), as they called the React handle.
import { PITCHES, captionAt, clock } from "../pitches.js";

function stop(ctx) {
  if (ctx.timer) clearInterval(ctx.timer);
  ctx.timer = null;
}

export default {
  initial: (ctx) => {
    ctx.at = 0; // the timer reads the time from here, as it read a ref
    return { id: "mdp", playing: false, at: 0, captions: true, transcript: false };
  },
  mounted(ctx, component) {
    ctx.registry.player = {
      open(next) {
        stop(ctx);
        ctx.at = 0;
        component.set((s) => ({ ...s, id: next, playing: false, at: 0, transcript: false }));
        try {
          if (ctx.dialog && !ctx.dialog.open) ctx.dialog.showModal();
        } catch {
          // A dialog that cannot open leaves the page as it was.
        }
      },
    };
  },
  vals(s, set, ctx) {
    const pitch = PITCHES[s.id];
    const caption = captionAt(s.id, s.at);
    const setAt = (value) => {
      ctx.at = value;
      set((now) => ({ ...now, at: value }));
    };
    return {
      dialogRef: (el) => {
        ctx.dialog = el;
      },
      player: {
        name: pitch.name,
        meta: pitch.meta,
        caption,
        pct: Math.round((s.at / pitch.dur) * 100),
        clock: `${clock(s.at)} / ${clock(pitch.dur)}`,
        lines: pitch.lines.map(([start, text]) => ({ at: clock(start), text, weight: text === caption && s.at > 0 ? "600" : "400" })),
      },
      playing: s.playing,
      paused: !s.playing,
      playLabel: s.playing ? "Pause" : s.at >= pitch.dur ? "Play again" : "Play",
      showCaption: s.captions && s.at > 0 && Boolean(caption),
      captionsOn: s.captions,
      transcriptOpen: s.transcript,
      togglePlay: () => {
        if (s.playing) {
          stop(ctx);
          set((now) => ({ ...now, playing: false }));
          return;
        }
        const dur = PITCHES[s.id].dur;
        set((now) => ({ ...now, playing: true }));
        if (ctx.at >= dur) setAt(0);
        stop(ctx);
        ctx.timer = setInterval(() => {
          const next = Math.min(dur, ctx.at + 0.25);
          if (next >= dur) {
            stop(ctx);
            set((now) => ({ ...now, playing: false }));
          }
          setAt(next);
        }, 250);
      },
      toggleCaptions: () => set((now) => ({ ...now, captions: !now.captions })),
      toggleTranscript: () => set((now) => ({ ...now, transcript: !now.transcript })),
      closePlayer: () => {
        if (ctx.dialog) ctx.dialog.close();
      },
      playerClosed: () => {
        stop(ctx);
        set((now) => ({ ...now, playing: false }));
      },
    };
  },
};
