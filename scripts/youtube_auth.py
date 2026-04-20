"""
Authentification OAuth 2.0 pour l'API YouTube Data v3.

Usage :
    python youtube_auth.py            # premier login interactif
    python youtube_auth.py --check    # verifie que le token stocke fonctionne

Au premier lancement : ouvre le navigateur, demande l'autorisation,
stocke le refresh token dans token.json. Les uploads ulterieurs sont
100% automatises.
"""
import argparse
import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']

HERE = Path(__file__).parent
CLIENT_SECRET = HERE / 'client_secret.json'
TOKEN_FILE = HERE / 'token.json'


def get_credentials():
    """Charge ou obtient des credentials valides."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print('Refresh du token...')
            creds.refresh(Request())
        else:
            print('Premier login : ouverture du navigateur...')
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        print(f'Token sauve : {TOKEN_FILE}')

    return creds


def check_identity():
    """Verifie que le token fonctionne et affiche la chaine selectionnee."""
    creds = get_credentials()
    yt = build('youtube', 'v3', credentials=creds)
    resp = yt.channels().list(part='snippet', mine=True).execute()
    items = resp.get('items', [])
    if not items:
        print('AUCUNE chaine trouvee pour ce compte.')
        return
    for ch in items:
        print(f"Chaine : {ch['snippet']['title']}")
        print(f"  ID   : {ch['id']}")
        print(f"  URL  : https://www.youtube.com/channel/{ch['id']}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true',
                   help='verifie que le token fonctionne')
    args = p.parse_args()

    if args.check:
        check_identity()
    else:
        get_credentials()
        print('\nAuth OK. Verification de la chaine :')
        check_identity()
