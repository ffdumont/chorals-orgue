"""
Enregistre automatiquement les 4 exemples + BWV 639 en MP3.
Capture le son systeme via WASAPI loopback (soundcard lib),
sauvegarde en WAV puis convertit en MP3 via ffmpeg.
"""
import soundcard as sc
import soundfile as sf
import mido
import numpy as np
import subprocess
import threading
import time
import random
import os

OUT_DIR = r'D:/Projects/chorals-orgue/assets/audio'
os.makedirs(OUT_DIR, exist_ok=True)

SAMPLE_RATE = 48000
FFMPEG = r'C:/Program Files/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'

CC = {
    'GO_bourdon8': 22, 'GO_flute8': 21, 'GO_prestant4': 23,
    'PED_soubasse': 40, 'PED_bourdon8': 42,
}

# ============ Recording helpers ============

class Recorder:
    def __init__(self):
        self.speaker = sc.default_speaker()
        self.mic = sc.get_microphone(id=str(self.speaker.name), include_loopback=True)
        self.recording = False
        self.buffer = []
        self.thread = None

    def _record_loop(self):
        with self.mic.recorder(samplerate=SAMPLE_RATE, channels=2) as rec:
            while self.recording:
                data = rec.record(numframes=1024)
                self.buffer.append(data)

    def start(self):
        self.buffer = []
        self.recording = True
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.start()
        time.sleep(0.1)  # warm-up

    def stop_and_save_wav(self, wav_path):
        self.recording = False
        self.thread.join()
        audio = np.concatenate(self.buffer, axis=0)
        sf.write(wav_path, audio, SAMPLE_RATE)
        print(f'  WAV: {wav_path} ({len(audio)/SAMPLE_RATE:.1f}s)')

def wav_to_mp3(wav_path, mp3_path):
    subprocess.run([FFMPEG, '-y', '-i', wav_path, '-codec:a', 'libmp3lame',
                    '-qscale:a', '2', mp3_path],
                   capture_output=True, check=True)
    os.remove(wav_path)
    print(f'  MP3: {mp3_path}')

# ============ MIDI playback functions ============

out = mido.open_output('loopMIDI Port 1')

def cc(name):
    out.send(mido.Message('control_change', channel=15, control=CC[name], value=127))
    time.sleep(0.05)

def non(ch, n, v=80):
    out.send(mido.Message('note_on', channel=ch, note=n, velocity=v))

def nof(ch, n):
    out.send(mido.Message('note_off', channel=ch, note=n, velocity=0))

def chord4_go(s, a, t, b, dur):
    for n in [b, t, a, s]:
        non(1, n)
        time.sleep(0.01)
    time.sleep(dur * 0.92)
    for n in [b, t, a, s]:
        nof(1, n)
    time.sleep(dur * 0.08)

def chord3_sap(s, a, bass, dur):
    non(0, bass)
    time.sleep(0.008)
    non(1, a)
    time.sleep(0.008)
    non(1, s)
    time.sleep(dur * 0.92)
    nof(0, bass)
    nof(1, a)
    nof(1, s)
    time.sleep(dur * 0.08)

def record_example(name, play_fn, stops_on, stops_off_after=None):
    if stops_off_after is None:
        stops_off_after = stops_on

    print(f'\n=== {name} ===')
    rec = Recorder()

    # Pull stops BEFORE recording starts
    for s in stops_on:
        cc(s)
    time.sleep(0.5)

    rec.start()
    time.sleep(0.3)  # short silence lead-in

    play_fn()

    time.sleep(1.0)  # tail
    wav = os.path.join(OUT_DIR, f'{name}.wav')
    mp3 = os.path.join(OUT_DIR, f'{name}.mp3')
    rec.stop_and_save_wav(wav)
    wav_to_mp3(wav, mp3)

    # Release stops
    for s in stops_off_after:
        cc(s)
    time.sleep(0.3)

# ============ Example 1: 4 voices SATB (all on GO) ============
def play_example1():
    # 4 accords, ronde chacun (3s)
    chord4_go(77, 72, 69, 53, 3)  # I
    chord4_go(77, 74, 70, 46, 3)  # IV
    chord4_go(76, 72, 67, 48, 3)  # V
    chord4_go(77, 72, 69, 53, 4)  # I

# ============ Example 2: 3 voices SAB ============
def play_example2():
    chord3_sap(72, 69, 53, 3)
    chord3_sap(74, 70, 46, 3)
    chord3_sap(76, 67, 48, 3)
    chord3_sap(77, 69, 53, 4)

# ============ Example 3: ornamented ============
def play_example3():
    random.seed(42)
    def play_orn(notes_with_dur):
        for n, d in notes_with_dur:
            j = random.uniform(0, 0.004)
            time.sleep(j)
            non(1, n)
            time.sleep(d * 0.9)
            nof(1, n)
            time.sleep(max(0, d * 0.1 - j))

    # Mesure 1: I (F), autour de Do5
    non(0, 53); non(1, 69)
    play_orn([(72, 0.4), (74, 0.35), (72, 0.35), (70, 0.35),
              (69, 0.35), (70, 0.35), (72, 0.35), (72, 0.4)])
    nof(0, 53); nof(1, 69)

    # Mesure 2: IV (Bb), autour de Re5
    non(0, 46); non(1, 70)
    play_orn([(74, 0.4), (75, 0.35), (74, 0.35), (72, 0.35),
              (70, 0.35), (72, 0.35), (74, 0.35), (74, 0.4)])
    nof(0, 46); nof(1, 70)

    # Mesure 3: V (C), autour de Mi5
    non(0, 48); non(1, 67)
    play_orn([(76, 0.4), (77, 0.35), (76, 0.35), (74, 0.35),
              (72, 0.35), (74, 0.35), (76, 0.35), (76, 0.4)])
    nof(0, 48); nof(1, 67)

    # Mesure 4: I (F), resolution
    non(0, 53); non(1, 69)
    play_orn([(77, 0.4), (79, 0.3), (81, 0.3), (79, 0.3),
              (77, 0.3), (76, 0.3), (77, 1.2)])
    nof(0, 53); nof(1, 69)

# ============ Example 4: BWV 639 style (from MIDI file) ============
def play_example4():
    mid = mido.MidiFile(r'D:/Projects/chorals-orgue/assets/midi/exemple4.mid')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

# ============ BWV 639 ============
def play_bwv639():
    mid = mido.MidiFile(r'D:/GrandOrgue/MIDI recordings/ich-ruf-zu-dir-orgue.mid')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

# ============ Run all ============

print('Preparation: rien ne doit jouer de son pendant l\'enregistrement !')
print('Assurez-vous que tout est silencieux, aucun notif...')
time.sleep(2)

# Exemples 1 et 2 n'ont pas de pedale separee dans la musique
# mais on tire les memes jeux pour la coherence
SAP = ['GO_flute8', 'GO_bourdon8', 'PED_soubasse']

record_example('exemple1', play_example1, SAP)
record_example('exemple2', play_example2, SAP)
record_example('exemple3', play_example3, SAP)
record_example('exemple4', play_example4, SAP)
record_example('bwv639', play_bwv639, SAP + ['PED_bourdon8'])

out.close()
print('\n=== TOUS LES ENREGISTREMENTS TERMINES ===')
print(f'Fichiers dans: {OUT_DIR}')
