"""Create original, sample-free audio fixtures for offline integration tests.

This bank is designed to test playback and arrangement coverage. It is not
the AI-produced research bank, which requires a separately audited provenance.
"""
import argparse
import hashlib
import json
import wave
from pathlib import Path

import numpy as np

from task import STAGES, system_choices

RATE = 16000
DURATION = 30


def arrangement(options):
    t = np.arange(RATE * DURATION) / RATE
    rhythm, harmony, instrument, ending = options
    roots = np.array([130.81, 110., 87.31, 98.])[np.minimum((t / 7.5).astype(int), 3)]
    beat = np.mod(t * (2 if rhythm == 0 else 3), 1)
    envelope = (1 - np.exp(-12 * beat)) * np.exp(-3 * beat)
    frequencies = roots * (1.5 if harmony == 0 else 2 ** (4 / 12))
    wave1 = np.sin(2 * np.pi * np.cumsum(roots) / RATE)
    phase = 2 * np.pi * np.cumsum(frequencies) / RATE
    wave2 = np.sin(phase) if instrument == 0 else (.75 * np.sin(phase) + .25 * np.sin(2 * phase))
    fade = np.clip((DURATION - t) / (2 if ending == 0 else 5), 0, 1)
    voice = (wave1 + .35 * wave2) * envelope * fade * np.minimum(t * 10, 1)
    return np.rint(32767 * .65 * voice / np.max(np.abs(voice))).astype("<i2")


def generate(folder):
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for index in range(16):
        choices = system_choices(index)
        name = "".join(map(str, choices)) + ".wav"
        path = folder / name
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            output.writeframes(arrangement(choices).tobytes())
        files.append({"path": name, "choices": dict(zip(STAGES, choices)),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"status": "SYNTHETIC_TECHNICAL_FIXTURE", "duration_seconds": DURATION,
                "sample_rate": RATE, "source": "original procedural tones", "files": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    generate(parser.parse_args().folder)
