"""Captions made from the transcript a founder types. Ported from apps/web/lib/captions.ts.

Nothing listens to the video, so each caption's timing is an estimate: the pitch's length
is shared out in proportion to the length of each piece of text. The founder is told this
when they add the transcript.
"""

from __future__ import annotations

import math
import re

from .validate import JS_SPACE_CLASS, js_len

MAX_CUE = 84


def _round3(n: float) -> float:
    return math.floor(n * 1000 + 0.5) / 1000


def caption_chunks(transcript: str) -> list[str]:
    """Splits text into sentences, then splits long sentences at word breaks."""
    clean = re.sub(JS_SPACE_CLASS + "+", " ", transcript).strip(" ")
    if not clean:
        return []
    sentences = [s.strip() for s in re.findall(r"[^.!?]+(?:[.!?]+|$)", clean)]
    sentences = [s for s in sentences if s] or [clean]
    chunks: list[str] = []
    for sentence in sentences:
        if js_len(sentence) <= MAX_CUE:
            chunks.append(sentence)
            continue
        line = ""
        for word in sentence.split(" "):
            if line and js_len(line) + 1 + js_len(word) > MAX_CUE:
                chunks.append(line)
                line = word
            else:
                line = f"{line} {word}" if line else word
        if line:
            chunks.append(line)
    return chunks


def cues_from_transcript(transcript: str, duration_seconds) -> list[dict]:
    """Shares the duration out across the chunks by their length."""
    chunks = caption_chunks(transcript)
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        return []
    if not chunks or not duration > 0:
        return []
    total = sum(js_len(c) for c in chunks)
    at = 0.0
    cues = []
    for i, text in enumerate(chunks):
        start = at
        end = duration if i == len(chunks) - 1 else at + (duration * js_len(text)) / total
        at = end
        cues.append({"start": _round3(start), "end": _round3(end), "text": text})
    return cues
