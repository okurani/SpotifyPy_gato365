import os
import requests
from authorize import get_spotify_access_token

import pandas as pd

def search_spotify(queries, access_token):
    search_results = []
    for query in queries:
        search_url = 'https://api.spotify.com/v1/search'
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'q': query, 'type': 'artist', 'limit': 1}  # Set limit to 1 for demo purposes
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 200:
            search_results.extend(response.json()['artists']['items'])
        else:
            print(f"Failed to search for {query}: {response.text}")
    return search_results

def get_artists(queries=None, ids=None, access_token=None):
    if queries is not None:
        search_results = search_spotify(queries, access_token)
        ids = [artist['id'] for artist in search_results]
    if not ids:
        raise ValueError("No artist ids provided or found.")
    url = 'https://api.spotify.com/v1/artists'
    headers = {'Authorization': f'Bearer {access_token}'}
    if len(ids) > 1:
        url += '?ids=' + ','.join(ids)
        response = requests.get(url, headers=headers)
    else:
        url += '/' + ids[0]
        response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get artist info: {response.text}")
    artist_data = response.json()
    if len(ids) > 1:
        artists = artist_data['artists']
    else:
        artists = [artist_data]  # Make single dict a list for uniform handling
    df = pd.DataFrame({
        'artist_id': [artist['id'] for artist in artists],
        'artist_name': [artist['name'] for artist in artists],
        'genres': [', '.join(artist['genres']) for artist in artists],
        'popularity': [artist['popularity'] for artist in artists],
        'type': [artist['type'] for artist in artists],
        'followers_total': [artist['followers']['total'] for artist in artists],
    })
    return df

def get_artist_projects(query=None, id=None, access_token=None, limit=20, offset=0):
    if query:
        access_token = get_spotify_access_token(client_id, client_secret)
        search_results = search_spotify([query], access_token)
        id = search_results[0]['id'] if search_results else None
    if not id:
        raise ValueError("Artist ID must be provided or found through a search query.")
    
    url = f'https://api.spotify.com/v1/artists/{id}/albums'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'include_groups': 'album,single',
        'market': 'US',
        'limit': limit,
        'offset': offset
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch albums: {response.text}")
    
    albums = response.json().get('items', [])
    df = pd.DataFrame.from_records(albums)
    df = df[['id', 'name', 'release_date', 'release_date_precision']].rename(columns={'id': 'album_id', 'name': 'album_name'}).drop_duplicates()
    return df

def get_related_artists(query=None, id=None, access_token=None):
    # If a query is provided, search for the artist to get the ID
    if query:
        search_results = search_spotify([query], access_token)
        if not search_results:
            raise ValueError(f"No artist found for query: {query}")
        id = search_results[0]['id']

    if not id:
        raise ValueError("Artist ID must be provided or found through a search query.")
    
    url = f"https://api.spotify.com/v1/artists/{id}/related-artists"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch related artists: {response.text}")
    
    related_artists = response.json()['artists']
    df = pd.DataFrame(related_artists)
    
    # Define columns to drop
    columns_to_drop = ['href', 'images', 'uri', 'external_urls', 'followers.href']
    # Check for the existence of each column before dropping
    columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    
    df = df.drop(columns=columns_to_drop)
    df = df.rename(columns={'id': 'artist_id', 'name': 'artist_name'})
    
    # Arrange columns in the specified order
    columns_order = ['genres', 'artist_id', 'artist_name', 'popularity', 'type', 'followers']
    df = df[columns_order]

    return df

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
access_token = get_spotify_access_token(client_id, client_secret)

related_artist_df = get_related_artists(query = "Taylor Swift", access_token=access_token)
print(related_artist_df)
