/**
 * Captions made from the transcript a founder types. Nothing listens to the
 * video, so each caption's timing is an estimate: the pitch's length is shared
 * out in proportion to the length of each piece of text. The founder is told
 * this when they add the transcript.
 */
export type Cue = { start: number; end: number; text: string };

const MAX_CUE = 84;

/** Splits text into sentences, then splits long sentences at word breaks. */
export function captionChunks(transcript: string): string[] {
  const clean = transcript.replace(/\s+/g, " ").trim();
  if (!clean) return [];
  const sentences = clean.match(/[^.!?]+(?:[.!?]+|$)/g)?.map((s) => s.trim()).filter(Boolean) ?? [clean];
  const chunks: string[] = [];
  for (const sentence of sentences) {
    if (sentence.length <= MAX_CUE) {
      chunks.push(sentence);
      continue;
    }
    let line = "";
    for (const word of sentence.split(" ")) {
      if (line && line.length + 1 + word.length > MAX_CUE) {
        chunks.push(line);
        line = word;
      } else {
        line = line ? `${line} ${word}` : word;
      }
    }
    if (line) chunks.push(line);
  }
  return chunks;
}

/** Shares the duration out across the chunks by their length. */
export function cuesFromTranscript(transcript: string, durationSeconds: number): Cue[] {
  const chunks = captionChunks(transcript);
  const duration = Number(durationSeconds);
  if (!chunks.length || !(duration > 0)) return [];
  const total = chunks.reduce((n, c) => n + c.length, 0);
  let at = 0;
  return chunks.map((text, i) => {
    const start = at;
    const end = i === chunks.length - 1 ? duration : at + (duration * text.length) / total;
    at = end;
    return { start: round(start), end: round(end), text };
  });
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
