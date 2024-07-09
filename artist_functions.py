import os
import requests
from authorize import get_spotify_access_token
from constants import pitch_class_lookup
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

def get_album_tracks(album_id, access_token, limit=20, offset=0):
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'market': 'US', 'limit': limit, 'offset': offset}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to get album tracks info: {response.text}")
    tracks = response.json()['items']
    df = pd.DataFrame({
        'track_id': [track['id'] for track in tracks],
        'track_name': [track['name'] for track in tracks],
        'disc_number': [track['disc_number'] for track in tracks],
        'duration_ms': [track['duration_ms'] for track in tracks],
        'explicit': [track['explicit'] for track in tracks],
        'popularity': [None] * len(tracks),  # Placeholder, popularity is not in album tracks response
        'artist_id': [', '.join([artist['id'] for artist in track['artists']]) for track in tracks],
        'artist_name': [', '.join([artist['name'] for artist in track['artists']]) for track in tracks],
        'album_id': album_id
    })
    return df

def get_track_audio_features(ids, access_token):
    if len(ids) > 100:
        raise ValueError("The maximum length of the ids vector is 100. Please shorten the length of the input vector.")
    
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

def get_artist_audio_features(query=None, id=None, access_token=None):
    authorization = get_spotify_access_token(client_id, client_secret)
    
    # Get artist information
    info = get_artists(queries=[query] if query else None, ids=[id] if id else None, access_token=authorization)
    if info.empty:
        raise ValueError("No artist found with the inputted ID. Please try again with a different ID.")
    
    artist_id = info['artist_id'].iloc[0]
    artist_name = info['artist_name'].iloc[0]
    
    # Get albums for the artist
    albums = get_artist_projects(id=artist_id, access_token=authorization)
    if albums.empty:
        raise ValueError("No albums found with the inputted ID. Please try again with a different ID.")
    
    # Paginate through many albums
    num_loops = (len(albums) + 49) // 50
    if num_loops > 1:
        all_albums = []
        for i in range(num_loops):
            more_albums = get_artist_projects(id=artist_id, offset=i*50, access_token=authorization)
            all_albums.append(more_albums)
        albums = pd.concat(all_albums).reset_index(drop=True)

    # Process album release year based on precision
    albums['album_release_year'] = albums.apply(lambda row: int(row['release_date'][:4]) if row['release_date_precision'] == 'year' else int(row['release_date'][:4]) if row['release_date_precision'] == 'day' else None, axis=1)
    
    # Retrieve tracks for each album
    tracks = pd.concat([get_album_tracks(album_id=album_id, access_token=authorization) for album_id in albums['album_id']])
    
    # Paginate through tracks if necessary
    num_loops_tracks = (len(tracks) + 99) // 100
    track_audio_features = pd.concat([get_track_audio_features(ids=tracks['track_id'].iloc[i*100:(i+1)*100].tolist(), access_token=authorization) for i in range(num_loops_tracks)])

    # Merge track details with audio features
    tracks = tracks.merge(track_audio_features, on='track_id', how='left')

    # Prepare final DataFrame
    albums = albums.assign(artist_name=artist_name, artist_id=artist_id)
    result = albums[['artist_name', 'artist_id', 'album_id', 'release_date', 'album_release_year', 'release_date_precision', 'album_name']]
    result = result.merge(tracks, on='album_id', how='left')

    # Further processing on keys and modes
    result['key_name'] = result['key'].apply(lambda x: pitch_class_lookup.get(x, 'Unknown'))
    result['mode_name'] = result['mode'].apply(lambda x: 'major' if x == 1 else 'minor' if x == 0 else None)
    result['key_mode'] = result.apply(lambda row: f"{row['key_name']} {row['mode_name']}", axis=1)

    # Clean up and rename as necessary
    result = result.rename(columns={'duration_ms_x': 'duration_ms'})
    result = result.drop(columns=['artist_name_y', 'artist_id_y', 'duration_ms_y'])

    return result

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
access_token = get_spotify_access_token(client_id, client_secret)


def get_artists_summary(queries=None, ids=None, access_token=None):
    if queries:
        summaries = [get_artist_summary(query=query, access_token=access_token) for query in queries]
    elif ids:
        summaries = [get_artist_summary(id=artist_id, access_token=access_token) for artist_id in ids]
    else:
        raise ValueError("Either queries or ids must be provided.")

    return pd.concat(summaries, ignore_index=True)

def get_artist_summary(query=None, id=None, access_token=None):
    # Get artist information
    artist = get_artists(queries=[query] if query else None, ids=[id] if id else None, access_token=access_token)
    artist = artist[['artist_name', 'artist_id']]
    
    # Get artist audio features
    features = get_artist_audio_features(query=query, id=id, access_token=access_token)

    # Calculate number of songs
    num_songs = features.shape[0]

    # Create summary statistics
    summary = features[['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 
                        'instrumentalness', 'liveness', 'valence', 'explicit', 'tempo', 'duration_ms', 'mode']].agg(['mean', 'std']).T.reset_index()
    summary.columns = ['feature', 'mean', 'std']

    # Add artist information
    result = pd.DataFrame({'artist_name': [artist['artist_name'].iloc[0]], 
                           'artist_id': [artist['artist_id'].iloc[0]], 
                           'num_songs': [num_songs]})
    
    # Combine results
    for index, row in summary.iterrows():
        result[row['feature'] + '_mean'] = row['mean']
        result[row['feature'] + '_std'] = row['std']

    return result

queries = ["Taylor Swift", "Sam Hunt"]
artists_summary = get_artists_summary(queries = queries, access_token=access_token)
print(artists_summary)
