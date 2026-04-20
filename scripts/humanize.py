"""
Humanise un fichier MIDI pour eviter le rendu trop mecanique.

Deux modifications :
1. Jitter sur les attaques (+/- quelques ms) pour desynchroniser les notes simultanees
2. Articulation : chaque note est raccourcie de quelques % pour creer une respiration

Usage :
    python humanize.py source.mid sortie.mid
    python humanize.py source.mid sortie.mid --jitter 10 --articulation 0.08
"""
import argparse
import mido
import random


def humanize(src_path, dst_path, jitter_ms=8, articulation_max=0.08, seed=42):
    random.seed(seed)
    mid = mido.MidiFile(src_path)
    tpq = mid.ticks_per_beat

    # Estimation simple : on utilise un tempo par defaut de 35 BPM
    # pour convertir ms -> ticks (adapter si tempo different connu)
    # Plus precis : lire le tempo dans les meta events
    tempo_us = 1714285  # ~35 BPM
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo_us = msg.tempo
                break
    jitter_ticks = int(jitter_ms * tpq / (tempo_us / 1000))

    new_tracks = []

    for track in mid.tracks:
        # Convertir en events avec temps absolu
        events = []
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            events.append([abs_tick, msg.copy(time=0)])

        # Appairer note_on / note_off
        notes_on = {}
        pairs = []
        for i, (t, m) in enumerate(events):
            if m.type == 'note_on' and m.velocity > 0:
                key = (m.channel, m.note)
                notes_on.setdefault(key, []).append(i)
            elif m.type == 'note_off' or (m.type == 'note_on' and m.velocity == 0):
                key = (m.channel, m.note)
                if key in notes_on and notes_on[key]:
                    pairs.append((notes_on[key].pop(0), i))

        new_times = {i: t for i, (t, _) in enumerate(events)}

        for start_i, end_i in pairs:
            s = events[start_i][0]
            e = events[end_i][0]
            dur = e - s

            # Jitter sur l'attaque
            new_s = s + random.randint(-jitter_ticks, jitter_ticks)
            # Articulation : raccourcir
            shorten = int(dur * random.uniform(0.03, articulation_max))
            new_e = e - shorten
            if new_e <= new_s:
                new_e = new_s + 1

            new_times[start_i] = max(0, new_s)
            new_times[end_i] = new_e

        # Reconstruire la piste
        order = sorted(range(len(events)), key=lambda i: new_times[i])
        new_track = mido.MidiTrack()
        prev = 0
        for i in order:
            t = new_times[i]
            m = events[i][1]
            delta = max(0, t - prev)
            prev = t
            new_track.append(m.copy(time=delta))
        new_tracks.append(new_track)

    out = mido.MidiFile(ticks_per_beat=tpq)
    out.tracks = new_tracks
    out.save(dst_path)
    print(f'Sauvegarde : {dst_path}')
    print(f'  jitter : +/- {jitter_ms} ms')
    print(f'  articulation : jusqu\'a -{int(articulation_max*100)}%')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('src', help='MIDI source')
    p.add_argument('dst', help='MIDI sortie')
    p.add_argument('--jitter', type=float, default=8, help='jitter en ms (defaut 8)')
    p.add_argument('--articulation', type=float, default=0.08,
                   help='raccourcissement max 0..1 (defaut 0.08 = 8%)')
    p.add_argument('--seed', type=int, default=42)
    args = p.parse_args()
    humanize(args.src, args.dst, args.jitter, args.articulation, args.seed)
