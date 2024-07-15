import os
import requests
from authorize import get_spotify_access_token
from authorize import search_spotify

import pandas as pd


def get_track_audio_features(queries=None, ids=None, access_token=None):
    if ids and len(ids) > 100:
        raise ValueError("The maximum length of the ids vector is 100. Please shorten the length of the input vector.")
    
    if queries is not None:
        search_results = search_spotify(queries, "track", access_token=access_token)
        ids = [track['id'] for track in search_results]
    
    if not ids:
        raise ValueError("No track ids provided or found.")
    
    url = 'https://api.spotify.com/v1/audio-features'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'ids': ','.join(ids)}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get track audio features: {response.text}")
    
    result = response.json()['audio_features']
    
    df = pd.DataFrame(result)
    df = df.drop(columns=['type', 'uri', 'track_href', 'analysis_url'])
    df = df.rename(columns={'id': 'track_id'})
    
    return df



def get_albums(queries=None, ids=None, access_token=None):
     if queries is not None:
        search_results = search_spotify(queries, "album", access_token)
        ids = [album['id'] for album in search_results]
     if not ids:
        raise ValueError("No album ids provided or found.")
     
     url = 'https://api.spotify.com/v1/albums'
     headers = {'Authorization': f'Bearer {access_token}'}
     if len(ids) > 1:
        url += '?ids=' + ','.join(ids) + '&market=US'
        response = requests.get(url, headers=headers)
     else:
        url += '/' + ids[0] + '?market=US'
        response = requests.get(url, headers=headers)
     if response.status_code != 200:
        raise Exception(f"Failed to get album info: {response.text}")
     album_data = response.json()
     if len(ids) > 1:
        albums = album_data['albums']
     else:
        albums = [album_data]

     data = []
     for album in albums:
        for artist in album['artists']:
            data.append({
                'album_id': album['id'],
                'label': album['label'],
                'album_name': album['name'],
                'artist_id': artist['id'],
                'artist_name': artist['name'],
                'release_date': album['release_date'],
                'total_tracks': album['total_tracks'],
                'album_type': album['album_type'],
                'popularity': album.get('popularity', None)  # Not all responses might have popularity
             })
            
     df = pd.DataFrame(data)
     return df


def get_album_tracks(query=None, ids=None, access_token=None, limit=20, offset=0):
    if query is not None:
        search_url = "https://api.spotify.com/v1/search"
        search_headers = {'Authorization': f'Bearer {access_token}'}
        search_params = {'q': query, 'type': 'album', 'market': 'US', 'limit': 1}
        search_response = requests.get(search_url, headers=search_headers, params=search_params)

        if search_response.status_code != 200:
            raise Exception(f"Failed to search for album: {search_response.text}")
        search_results = search_response.json()
        ids = [album['id'] for album in search_results['albums']['items']] if search_results['albums']['items'] else None

    if not ids:
        raise ValueError("No album ids provided or found.")
    
    if len(ids) == 1:
        # Fetch tracks for a single album
        url = f"https://api.spotify.com/v1/albums/{ids[0]}/tracks"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'market': 'US', 'limit': limit, 'offset': offset}
        response = requests.get(url, headers=headers, params=params)
    else:
        url = "https://api.spotify.com/v1/albums"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'ids': ','.join(ids), 'market': 'US', 'limit': limit, 'offset': offset}
        response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Failed to get album tracks info: {response.text}")
   
    tracks_data = response.json()['items'] if len(ids) == 1 else [track for album in response.json()['albums'] for track in album['tracks']['items']]
    df = pd.DataFrame({
        'track_id': [track['id'] for track in tracks_data],
        'track_name': [track['name'] for track in tracks_data],
        'disc_number': [track['disc_number'] for track in tracks_data],
        'duration_ms': [track['duration_ms'] for track in tracks_data],
        'explicit': [track['explicit'] for track in tracks_data],
        'popularity': [None] * len(tracks_data),  # Popularity is not provided in this API response
        'artist_id': [', '.join([artist['id'] for artist in track['artists']]) for track in tracks_data],
        'artist_name': [', '.join([artist['name'] for artist in track['artists']]) for track in tracks_data],
        'album_id': ids[0] if len(ids) == 1 else ', '.join(ids)
    })
    return df


def get_artist_albums(query=None, id=None, limit=20, offset=0, access_token=None):
    if query is not None:
        search_url = 'https://api.spotify.com/v1/search'
        search_params = {
            'q': query,
            'type': 'artist',
            'limit': 1
        }
        headers = {
            'Authorization': 'Bearer ' + access_token
        }
        search_response = requests.get(search_url, params=search_params, headers=headers)
        search_response.raise_for_status()
        search_results = search_response.json()
        if 'artists' in search_results and 'items' in search_results['artists']:
            id = search_results['artists']['items'][0]['id']

    url = f'https://api.spotify.com/v1/artists/{id}/albums'
    params = {
        'include_groups': 'album',
        'market': 'US',
        'limit': limit,
        'offset': offset
    }
    headers = {
        'Authorization': 'Bearer ' + access_token
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    result = response.json()

    albums = result.get('items', [])
    cleaned_albums = []
    for album in albums:
        artists = [{'id': artist['id'], 'name': artist['name']} for artist in album['artists']]
        cleaned_album = {
            'album_type': album['album_type'],
            'album_id': album['id'],
            'album_name': album['name'],
            'release_date': album['release_date'],
            'total_tracks': album['total_tracks'],
            'artist_id': ', '.join(artist['id'] for artist in artists),
            'artist_name': ', '.join(artist['name'] for artist in artists)
        }
        cleaned_albums.append(cleaned_album)

    results = pd.DataFrame(cleaned_albums)
    return results


def get_album_summary(query=None, id=None, access_token=None):
    if query is not None:
        search_results = search_spotify([query], "album", access_token)
        id = [album['id'] for album in search_results]

    if not id:
        raise ValueError("No album id provided or found.")

    album = get_albums(ids=id, access_token=access_token)
    tracks = get_album_tracks(ids=id, access_token=access_token)
    features = get_track_audio_features(ids=tracks['track_id'].tolist(), access_token=access_token)

    summary = features[['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'duration_ms', 'mode']].agg(['mean', 'std'])
    summary_flat = summary.unstack().to_frame().T
    summary_flat.columns = [f"{stat}_{feat}" for feat, stat in summary_flat.columns]

    result = pd.concat([album.reset_index(drop=True), summary_flat.reset_index(drop=True)], axis=1)
    result = result.drop(columns=['label', 'release_date', 'artist_id', 'artist_name'])

    return result


def get_album_track_features(query=None, ids=None, access_token=None):
    tracks = get_album_tracks(query=query, ids=ids, access_token=access_token)
    track_ids = tracks['track_id'].tolist()
    features = get_track_audio_features(ids=track_ids, access_token=access_token)

    result = pd.merge(tracks, features, on='track_id')
    result = result.drop(columns=['duration_ms_x', 'disc_number'])
    result = result.rename(columns={'duration_ms_y': 'duration_ms'})

    return result


client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
access_token = get_spotify_access_token(client_id, client_secret)

