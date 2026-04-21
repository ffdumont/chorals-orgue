"""
Capture video (ecran 2 = GrandOrgue) + audio (WASAPI loopback) synchronises.

Module :
    VideoRecorder().start() / stop_and_save_mp4(out_path)

Le module gere :
    - ffmpeg gdigrab sur l'ecran 2 (offset_x=1920, y=1, 1920x1080) vers un .mkv temporaire
    - soundcard (loopback WASAPI) en thread Python, vers un .wav temporaire
    - mux final en MP4 (H264 + AAC) et nettoyage des temporaires
    - ecriture optionnelle d'un manifest de synchro <key>.sync.json qui
      ancre les barres de mesure MIDI sur le referentiel temporel du MP4
      (detection du premier onset audible). Voir write_sync_manifest().

CLI :
    python record_video.py fichier.mid --stops fonde --out ../assets/video/sortie.mp4
"""
import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import soundcard as sc
import soundfile as sf

FFMPEG = r'C:/Program Files/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'
SAMPLE_RATE = 48000


def detect_first_onset(audio, sample_rate, threshold_db=-40.0,
                       smooth_ms=20.0, max_search_s=10.0, skip_ms=0.0):
    """Retourne le temps (sec) du premier onset audible dans `audio`.

    `audio` : numpy array (mono ou stereo).
    Algorithme : enveloppe = moving average de |audio| sur smooth_ms,
    premier index ou l'enveloppe depasse le seuil (convertit depuis dBFS).
    On cherche dans les `max_search_s` premieres secondes seulement.
    `skip_ms` : skippe les N premiers ms (utile si la capture demarre par un
    click parasite — p.ex. warmup GrandOrgue qui reverbe dans la suite).
    Retourne None si aucun onset n'est detecte.
    """
    if audio.ndim > 1:
        mono = audio.mean(axis=1)
    else:
        mono = audio
    max_samples = int(sample_rate * max_search_s)
    skip_samples = int(sample_rate * skip_ms / 1000)
    mono = mono[skip_samples:skip_samples + max_samples]
    if len(mono) == 0:
        return None
    threshold = 10.0 ** (threshold_db / 20.0)
    window = max(1, int(sample_rate * smooth_ms / 1000))
    abs_audio = np.abs(mono).astype(np.float32)
    kernel = np.ones(window, dtype=np.float32) / window
    envelope = np.convolve(abs_audio, kernel, mode='valid')
    above = envelope > threshold
    if not above.any():
        return None
    idx = int(np.argmax(above))
    return (skip_samples + idx) / sample_rate

# Ecran 2 (GrandOrgue) d'apres System.Windows.Forms.Screen
SCREEN_OFFSET_X = 1920
SCREEN_OFFSET_Y = 1
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
VIDEO_FPS = 30


class VideoRecorder:
    """Capture ecran 2 + audio loopback, mux en MP4 a l'arret."""

    def __init__(self, tmp_dir=None):
        self.tmp_dir = Path(tmp_dir) if tmp_dir else Path(tempfile.gettempdir())
        self.video_tmp = None
        self.audio_tmp = None
        self.ffmpeg_proc = None
        self.audio_thread = None
        self.audio_buffer = []
        self.recording = False
        # Apres stop_and_save_mp4, `audio_captured` conserve le numpy array
        # audio (avant mux) pour detection d'onset / construction du manifest.
        self.audio_captured = None

    def _record_audio(self):
        speaker = sc.default_speaker()
        mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        with mic.recorder(samplerate=SAMPLE_RATE, channels=2) as rec:
            while self.recording:
                self.audio_buffer.append(rec.record(numframes=1024))

    def start(self):
        ts = int(time.time() * 1000)
        self.video_tmp = self.tmp_dir / f'vid_{ts}.mkv'
        self.audio_tmp = self.tmp_dir / f'aud_{ts}.wav'

        # Video : ffmpeg gdigrab ecran 2
        cmd = [
            FFMPEG, '-y',
            '-f', 'gdigrab',
            '-framerate', str(VIDEO_FPS),
            '-offset_x', str(SCREEN_OFFSET_X),
            '-offset_y', str(SCREEN_OFFSET_Y),
            '-video_size', f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}',
            '-i', 'desktop',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            str(self.video_tmp),
        ]
        self.ffmpeg_proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        # Audio : thread soundcard
        self.audio_buffer = []
        self.recording = True
        self.audio_thread = threading.Thread(target=self._record_audio)
        self.audio_thread.start()

        time.sleep(0.3)  # warm-up video + audio

    def stop_and_save_mp4(self, out_path):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Stop audio d'abord (thread rapide)
        self.recording = False
        self.audio_thread.join()
        audio = np.concatenate(self.audio_buffer, axis=0)
        self.audio_captured = audio  # garde pour write_sync_manifest()
        sf.write(str(self.audio_tmp), audio, SAMPLE_RATE)

        # Stop ffmpeg video proprement (envoie 'q' sur stdin)
        try:
            self.ffmpeg_proc.stdin.write(b'q')
            self.ffmpeg_proc.stdin.flush()
        except Exception:
            pass
        self.ffmpeg_proc.wait(timeout=10)

        # Mux video + audio en MP4 final
        mux_cmd = [
            FFMPEG, '-y',
            '-i', str(self.video_tmp),
            '-i', str(self.audio_tmp),
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            str(out_path),
        ]
        subprocess.run(mux_cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup temporaires
        for f in (self.video_tmp, self.audio_tmp):
            try:
                os.remove(f)
            except OSError:
                pass

        duration = len(audio) / SAMPLE_RATE
        print(f'  MP4: {out_path} ({duration:.1f}s)')
        return out_path

    def write_sync_manifest(self, key, midi_path, out_dir,
                            threshold_db=-40.0, skip_ms=0.0):
        """Detecte le premier onset audible + genere `<key>.sync.json`.

        `key`         : basename (sans extension) utilise pour le fichier.
        `midi_path`   : chemin vers le .mid source (pour extraire onsets/barlines).
        `out_dir`     : repertoire de sortie (ex. assets/sync/).
        `threshold_db`: seuil de detection de l'onset (dBFS). -40 par defaut.
        `skip_ms`     : skippe les N premiers ms de l'audio (utile si un click
                        parasite precede le vrai premier onset).

        Le manifest exprime `onsets_mp4` et `barlines_mp4` dans le referentiel
        temporel du MP4 : onset_mp4 = first_onset_mp4 + (midi_time - midi_t0).
        Suppose que la MIDI a ete joue via mid.play() (fidele au tempo du .mid).
        Pour les captures hand-coded qui divergent du .mid (ex. exemple1/2/3),
        une derive interne est possible ; seul le premier onset est sur.
        """
        if self.audio_captured is None:
            raise RuntimeError("audio_captured vide : appeler apres stop_and_save_mp4()")
        # Import tardif pour eviter une dependance circulaire au niveau module
        from build_scores import extract_barlines, extract_onsets

        first_onset = detect_first_onset(
            self.audio_captured, SAMPLE_RATE,
            threshold_db=threshold_db, skip_ms=skip_ms,
        )
        if first_onset is None:
            print(f'  WARN: premier onset non detecte, sync.json ignore.')
            return None

        midi_onsets = extract_onsets(Path(midi_path))
        midi_barlines = extract_barlines(Path(midi_path))
        t0_midi = midi_onsets[0] if midi_onsets else 0.0
        barlines_mp4 = [round(b - t0_midi + first_onset, 4) for b in midi_barlines]
        onsets_mp4 = [round(o - t0_midi + first_onset, 4) for o in midi_onsets]

        manifest = {
            "version": 1,
            "source": "capture",
            "first_onset_mp4": round(first_onset, 4),
            "barlines_mp4": barlines_mp4,
            "onsets_mp4": onsets_mp4,
            "audio_duration": round(len(self.audio_captured) / SAMPLE_RATE, 3),
        }
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{key}.sync.json"
        out_path.write_text(json.dumps(manifest, separators=(",", ":")))
        print(f'  sync: {out_path} (first_onset_mp4={first_onset:.3f}s)')
        return out_path


def _play_midi_file(path, port_name='loopMIDI Port 1', preset=None):
    """Mini-lecteur pour l'usage CLI. Pour les scripts avances, utiliser
    directement VideoRecorder et jouer le MIDI depuis le script appelant."""
    import mido
    from stops_control_sjdl import Stops, PRESETS

    out = mido.open_output(port_name)
    stops = None
    if preset:
        stops = Stops(out)
        stops.toggle_many(PRESETS[preset])
        time.sleep(0.5)

    mid = mido.MidiFile(path)
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

    if stops:
        time.sleep(0.3)
        stops.toggle_many(PRESETS[preset])
    out.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('midi', help='fichier .mid a jouer')
    p.add_argument('--stops', default=None, help='preset (doux, fonde, plein_jeu)')
    p.add_argument('--out', required=True, help='chemin du .mp4 de sortie')
    p.add_argument('--lead', type=float, default=0.5,
                   help='silence avant playback (s)')
    p.add_argument('--tail', type=float, default=1.0,
                   help='queue apres playback (s)')
    args = p.parse_args()

    rec = VideoRecorder()
    print(f'Capture ecran 2 + audio -> {args.out}')
    rec.start()
    time.sleep(args.lead)

    _play_midi_file(args.midi, preset=args.stops)

    time.sleep(args.tail)
    rec.stop_and_save_mp4(args.out)
    print('Termine.')
