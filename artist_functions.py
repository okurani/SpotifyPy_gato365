import os
import requests
from authorize import get_spotify_access_token
from authorize import search_spotify
from constants import pitch_class_lookup
import pandas as pd

def get_artists(queries=None, ids=None, access_token=None):
    if queries is not None:
        search_results = search_spotify(queries, "artist", access_token)
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
        search_results = search_spotify([query],"artist", access_token)
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
        search_results = search_spotify([query], "artist",access_token)
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

def get_album_tracks(query=None, ids=None, access_token=None, limit=20, offset=0):
    if query is not None:
        # Search for the album by name and get the ID
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

    # Check if single ID or multiple IDs are provided
    if len(ids) == 1:
        # Fetch tracks for a single album
        url = f"https://api.spotify.com/v1/albums/{ids[0]}/tracks"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'market': 'US', 'limit': limit, 'offset': offset}
        response = requests.get(url, headers=headers, params=params)
    else:
        # Fetch tracks for multiple albums (not typical but supported)
        url = "https://api.spotify.com/v1/albums"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'ids': ','.join(ids), 'market': 'US', 'limit': limit, 'offset': offset}
        response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Failed to get album tracks info: {response.text}")
    
    # Extract and transform track data into DataFrame
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
    # Retrieve tracks for each album
    tracks = pd.concat([get_album_tracks(ids=[album_id], access_token=authorization) for album_id in albums['album_id']])

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

def get_artist_top_tracks(query=None, id=None, access_token=None):
    # If a query is provided, search for the artist to get the ID
    if query:
        search_results = search_spotify([query], "artist",access_token)
        if not search_results:
            raise ValueError(f"No artist found for query: {query}")
        id = search_results[0]['id']

    if not id:
        raise ValueError("Artist ID must be provided or found through a search query.")
    
    url = f"https://api.spotify.com/v1/artists/{id}/top-tracks"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'market': 'US'}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch top tracks: {response.text}")
    
    top_tracks = response.json()['tracks']
    df = pd.DataFrame(top_tracks)
    
    # Process artist information within the tracks
    df['artists'] = df['artists'].apply(lambda artists: [{'id': artist['id'], 'name': artist['name']} for artist in artists])
    df['artist_id'] = df['artists'].apply(lambda artists: ', '.join([artist['id'] for artist in artists]))
    df['artist_name'] = df['artists'].apply(lambda artists: ', '.join([artist['name'] for artist in artists]))

    # Define columns to drop and check for their existence
    columns_to_drop = [
        'href', 'is_local', 'is_playable', 'preview_url', 'uri', 
        'album.artists', 'album.href', 'album.images', 'album.is_playable',
        'album.release_date', 'album.release_date_precision', 'album.total_tracks',
        'album.type', 'album.uri', 'album.external_urls.spotify',
        'external_ids.isrc', 'external_urls.spotify', 'artists'
    ]
    columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    
    df = df.drop(columns=columns_to_drop)
    df = df.rename(columns={
        'id': 'track_id',
        'album.album_type': 'album_type',
        'album.name': 'album_name',
        'name': 'track_name',
        'album.id': 'album_id'
    })

    # Check for existence of columns to rearrange
    columns_order = [
        'track_name', 'track_id', 'artist_name', 'artist_id', 
        'album_name', 'album_id', 'album_type', 'popularity', 
        'disc_number', 'duration_ms', 'explicit', 'track_number'
    ]
    columns_order = [col for col in columns_order if col in df.columns]
    df = df[columns_order]

    return df

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
access_token = get_spotify_access_token(client_id, client_secret)
#queries = ["Taylor Swift", "Gracie Abrams"]
artist_df = get_artist_top_tracks(query = "Taylor Swift", access_token=access_token)
print(artist_df)