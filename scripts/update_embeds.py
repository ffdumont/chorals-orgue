"""
Remplace les balises <audio> des pages markdown par des iframes YouTube,
en s'appuyant sur le mapping scripts/video_ids.yml.

Usage :
    python update_embeds.py              # applique les changements
    python update_embeds.py --dry-run    # affiche sans modifier

Pour chaque <audio> qui reference /chorals-orgue/assets/audio/<key>.mp3 :
    - si <key> est dans video_ids.yml : remplace par une iframe
    - sinon : laisse intact et avertit
"""
import argparse
import re
from pathlib import Path

import yaml

HERE = Path(__file__).parent
ROOT = HERE.parent
PIECES_DIR = ROOT / 'pieces'
MAPPING_FILE = HERE / 'video_ids.yml'

# Match:
#   <audio controls style="...">
#     <source src="/chorals-orgue/assets/audio/KEY.mp3" type="audio/mpeg">
#     ... (texte optionnel de fallback)
#   </audio>
AUDIO_RE = re.compile(
    r'<audio[^>]*>\s*'
    r'<source\s+src="[^"]*?/assets/audio/([^"/]+)\.mp3"[^>]*>'
    r'.*?</audio>',
    re.DOTALL,
)


def iframe_html(video_id, title='Vidéo'):
    return (
        '<div style="position:relative;padding-bottom:56.25%;height:0;'
        'overflow:hidden;max-width:100%;margin:1em 0;">\n'
        '  <iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" '
        f'src="https://www.youtube.com/embed/{video_id}" '
        f'title="{title}" frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        'gyroscope; picture-in-picture" '
        'allowfullscreen></iframe>\n'
        '</div>'
    )


def process_file(md_path, mapping, dry_run=False):
    text = md_path.read_text(encoding='utf-8')
    replaced = 0
    missing = []

    def repl(m):
        nonlocal replaced
        key = m.group(1)
        if key in mapping:
            replaced += 1
            return iframe_html(mapping[key], title=key)
        missing.append(key)
        return m.group(0)

    new_text = AUDIO_RE.sub(repl, text)

    if new_text != text and not dry_run:
        md_path.write_text(new_text, encoding='utf-8')

    return replaced, missing


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    if not MAPPING_FILE.exists():
        print(f'Mapping absent : {MAPPING_FILE}')
        print('Lance d\'abord upload_youtube.py pour peupler le mapping.')
        return 1

    mapping = yaml.safe_load(MAPPING_FILE.read_text(encoding='utf-8')) or {}
    if not mapping:
        print('Mapping vide.')
        return 1

    print(f'{len(mapping)} entrees dans le mapping.')
    total_replaced = 0
    all_missing = set()

    for md in sorted(PIECES_DIR.glob('*.md')):
        replaced, missing = process_file(md, mapping, args.dry_run)
        if replaced:
            verb = 'remplacerait' if args.dry_run else 'remplace'
            print(f'  {md.relative_to(ROOT)} : {verb} {replaced}')
            total_replaced += replaced
        for k in missing:
            all_missing.add(k)

    print(f'\nTotal : {total_replaced} iframe(s) '
          f'{"a generer" if args.dry_run else "ecrites"}.')
    if all_missing:
        print(f'Cles <audio> sans mapping : {sorted(all_missing)}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
