import requests
from dotenv import load_dotenv

load_dotenv()

def get_spotify_access_token(client_id, client_secret):
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    })
    if auth_response.status_code != 200:
        raise Exception(f"Failed to get access token: {auth_response.text}")
    return auth_response.json()['access_token']



