"""Construit un manifest de synchro <video_id>.sync.json pour une video
YouTube existante (retrofit), sans recapture.

Telecharge l'audio via yt-dlp, detecte le premier onset audible (ou le
prend en override si passe via --first-onset-mp4), et compose le JSON en
combinant avec les barres de mesure MIDI.

Usage :
    # Auto-detection :
    python scripts/build_sync_retrofit.py bwv639 --video-id gKU9n1Uh6xI

    # Override manuel (utile quand l'intro video contient des transitoires
    # parasites — applaudissements, bruit de pedalier, etc.) :
    python scripts/build_sync_retrofit.py bwv572_gravement \\
        --video-id ott000oltCQ --first-onset-mp4 16.0

Sortie : assets/sync/<video_id>.sync.json (cle par video_id, pas par
midi_key, pour supporter plusieurs videos pour une meme piece).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_scores import extract_barlines, extract_onsets
from record_video import detect_first_onset

ROOT = Path(__file__).resolve().parent.parent
MIDI_DIR = ROOT / "assets" / "midi"
SYNC_DIR = ROOT / "assets" / "sync"


def download_youtube_audio(video_id: str, tmp_dir: Path) -> Path:
    """Telecharge l'audio d'une video YouTube en .wav. Retourne le chemin."""
    import yt_dlp

    out_template = str(tmp_dir / f"{video_id}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }],
        "quiet": True,
        "no_warnings": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    wav_path = tmp_dir / f"{video_id}.wav"
    if not wav_path.exists():
        raise FileNotFoundError(f"yt-dlp n'a pas produit {wav_path}")
    return wav_path


def build_manifest(midi_key: str, video_id: str,
                   first_onset_override: float | None = None,
                   threshold_db: float = -40.0,
                   skip_ms: float = 0.0) -> dict:
    midi_path = MIDI_DIR / f"{midi_key}.mid"
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI introuvable : {midi_path}")

    if first_onset_override is not None:
        first_onset = first_onset_override
        source = "retrofit_manual"
        audio_duration = None
        print(f"Override manuel : first_onset_mp4 = {first_onset:.3f}s")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            print(f"Telechargement audio YouTube {video_id}...")
            wav_path = download_youtube_audio(video_id, tmp_dir)
            audio, sr = sf.read(str(wav_path))
            audio_duration = round(len(audio) / sr, 3)
            print(f"Audio : {audio_duration}s @ {sr}Hz ({audio.shape})")
            first_onset = detect_first_onset(
                audio, sr, threshold_db=threshold_db, skip_ms=skip_ms,
                max_search_s=max(30.0, audio_duration * 0.25),
            )
        if first_onset is None:
            raise RuntimeError(
                "Premier onset non detecte. Essaie --threshold-db plus haut "
                "(ex. -50) ou passe --first-onset-mp4 <s> en override."
            )
        source = "retrofit_youtube"
        print(f"Detection auto : first_onset_mp4 = {first_onset:.3f}s")

    midi_onsets = extract_onsets(midi_path)
    midi_barlines = extract_barlines(midi_path)
    t0_midi = midi_onsets[0] if midi_onsets else 0.0
    barlines_mp4 = [round(b - t0_midi + first_onset, 4) for b in midi_barlines]
    onsets_mp4 = [round(o - t0_midi + first_onset, 4) for o in midi_onsets]

    manifest = {
        "version": 1,
        "source": source,
        "first_onset_mp4": round(first_onset, 4),
        "barlines_mp4": barlines_mp4,
        "onsets_mp4": onsets_mp4,
        "midi_key": midi_key,
        "video_id": video_id,
    }
    if audio_duration is not None:
        manifest["audio_duration"] = audio_duration
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("midi_key", help="Cle MIDI (ex. bwv572_gravement, bwv639)")
    p.add_argument("--video-id", required=True, help="ID YouTube (ex. gKU9n1Uh6xI)")
    p.add_argument("--first-onset-mp4", type=float, default=None,
                   help="Override manuel du premier onset (secondes). "
                        "Quand fourni, saute le telechargement et la detection auto.")
    p.add_argument("--threshold-db", type=float, default=-40.0,
                   help="Seuil de detection (dBFS). Defaut -40.")
    p.add_argument("--skip-ms", type=float, default=0.0,
                   help="Skipper les N premiers ms avant la detection "
                        "(utile pour ignorer un click ou une intro parasite).")
    args = p.parse_args()

    manifest = build_manifest(
        args.midi_key, args.video_id,
        first_onset_override=args.first_onset_mp4,
        threshold_db=args.threshold_db,
        skip_ms=args.skip_ms,
    )

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SYNC_DIR / f"{args.video_id}.sync.json"
    out_path.write_text(json.dumps(manifest, separators=(",", ":")))
    print(f"Ecrit : {out_path}")
    print(f"  barres : {len(manifest['barlines_mp4'])} entrees, "
          f"{manifest['barlines_mp4'][0]:.2f}s -> {manifest['barlines_mp4'][-1]:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
