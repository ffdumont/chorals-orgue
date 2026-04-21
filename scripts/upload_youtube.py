"""
Upload d'un MP4 sur YouTube en non-repertorie (unlisted), via l'API Data v3.

Usage :
    python upload_youtube.py --file ../assets/video/exemple4.mp4 \\
        --key exemple4 \\
        --title "BWV 639 - Exemple 4 (fonds)" \\
        --description "Extrait pedagogique, registration fonds de 8 + 4."

Met a jour scripts/video_ids.yml :
    exemple4: "YT_VIDEO_ID"

Les pages markdown sont ensuite regenerees par update_embeds.py.
"""
import argparse
import shutil
import sys
from pathlib import Path

import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from youtube_auth import get_credentials

HERE = Path(__file__).parent
MAPPING_FILE = HERE / 'video_ids.yml'
SYNC_DIR = HERE.parent / 'assets' / 'sync'

# Chunk size pour upload resumable (8 MB = bon compromis reseau/memoire)
CHUNK_SIZE = 8 * 1024 * 1024


def load_mapping():
    if MAPPING_FILE.exists():
        return yaml.safe_load(MAPPING_FILE.read_text(encoding='utf-8')) or {}
    return {}


def save_mapping(data):
    MAPPING_FILE.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=True),
        encoding='utf-8',
    )


def upload(file_path, title, description='', tags=None, category_id='10',
           privacy='unlisted'):
    """Upload un MP4. Retourne l'ID YouTube.

    category_id 10 = "Music".
    privacy : public | unlisted | private.
    """
    creds = get_credentials()
    yt = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or [],
            'categoryId': category_id,
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False,
        },
    }

    media = MediaFileUpload(
        str(file_path), chunksize=CHUNK_SIZE, resumable=True,
        mimetype='video/mp4',
    )

    print(f'Upload : {file_path}')
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        try:
            status, response = req.next_chunk()
            if status:
                print(f'  {int(status.progress() * 100)}%...')
        except HttpError as e:
            print(f'Erreur HTTP : {e}')
            raise

    video_id = response['id']
    url = f'https://youtu.be/{video_id}'
    print(f'  OK -> {url}')
    return video_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', required=True, help='chemin du MP4 a uploader')
    p.add_argument('--key', required=True,
                   help='cle pour le mapping (ex: exemple4, bwv639)')
    p.add_argument('--title', required=True)
    p.add_argument('--description', default='')
    p.add_argument('--tags', default='', help='tags separes par des virgules')
    p.add_argument('--privacy', default='unlisted',
                   choices=['public', 'unlisted', 'private'])
    args = p.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f'Fichier introuvable : {file_path}')
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    vid = upload(file_path, args.title, args.description, tags,
                 privacy=args.privacy)

    mapping = load_mapping()
    old = mapping.get(args.key)
    if old and old != vid:
        print(f'  (remplace ancien ID : {old})')
    mapping[args.key] = vid
    save_mapping(mapping)
    print(f'Mapping mis a jour : {MAPPING_FILE}')

    # Si un sync.json a ete produit a la capture (cle par midi_key), on le
    # copie sous la cle video_id — c'est cette cle-la que le JS charge en
    # priorite (permet plusieurs videos pour un meme .mid).
    capture_sync = SYNC_DIR / f'{args.key}.sync.json'
    video_sync = SYNC_DIR / f'{vid}.sync.json'
    if capture_sync.exists():
        shutil.copy2(capture_sync, video_sync)
        print(f'Sync copie : {capture_sync.name} -> {video_sync.name}')
    else:
        print(f'  (pas de sync.json trouve pour {args.key}, ignore)')


if __name__ == '__main__':
    main()
