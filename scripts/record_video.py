"""
Capture video (ecran 2 = GrandOrgue) + audio (WASAPI loopback) synchronises.

Module :
    VideoRecorder().start() / stop_and_save_mp4(out_path)

Le module gere :
    - ffmpeg gdigrab sur l'ecran 2 (offset_x=1920, y=1, 1920x1080) vers un .mkv temporaire
    - soundcard (loopback WASAPI) en thread Python, vers un .wav temporaire
    - mux final en MP4 (H264 + AAC) et nettoyage des temporaires

CLI :
    python record_video.py fichier.mid --stops fonde --out ../assets/video/sortie.mp4
"""
import argparse
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


def _play_midi_file(path, port_name='loopMIDI Port 1', preset=None):
    """Mini-lecteur pour l'usage CLI. Pour les scripts avances, utiliser
    directement VideoRecorder et jouer le MIDI depuis le script appelant."""
    import mido
    from stops_control import Stops, PRESETS

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
