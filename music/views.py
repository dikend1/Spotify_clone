from idlelib.rpc import response_queue

import requests
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
from bs4 import BeautifulSoup as bs4
import re
# Deezer API base URL
DEEZER_API_URL = "https://api.deezer.com"


def top_artists():
    url = f"{DEEZER_API_URL}/chart/0/artists"
    response = requests.get(url)
    response_data = response.json()

    artists_info = []
    if 'data' in response_data:
        for artist in response_data['data']:
            name = artist.get('name', 'No Name')
            avatar_url = artist.get('picture_big', 'No URL')
            artist_id = artist.get('id', 'No ID')
            artists_info.append((name, avatar_url, artist_id))

    return artists_info


def top_tracks():
    url = f"{DEEZER_API_URL}/chart/0/tracks"
    response = requests.get(url)
    data = response.json()
    track_details = []

    if 'data' in data:
        shortened_tracks = data['data'][:18]

        for track in shortened_tracks:
            track_id = track.get('id')
            track_name = track.get('title')
            artist_name = track.get('artist', {}).get('name', 'Unknown Artist')
            cover_url = track.get('album', {}).get('cover_big', 'No Cover')

            track_details.append({
                'id': track_id,
                'name': track_name,
                'artist': artist_name,
                'cover_url': cover_url,
            })

    return track_details

def get_track_details(track_id):
    """Получает детали трека с Deezer API"""
    url = f"{DEEZER_API_URL}/track/{track_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        track_name = data.get("title", "Unknown Track")
        artist_name = data.get("artist", {}).get("name", "Unknown Artist")
        track_image = data.get("album", {}).get("cover_big", "")
        audio_url = data.get("preview", "")  # Deezer предоставляет 30-секундный preview
        duration = data.get("duration", 0)

        # Форматируем длительность в мин:сек
        minutes = duration // 60
        seconds = duration % 60
        duration_text = f"{minutes}:{seconds:02d}"

        return {
            "track_name": track_name,
            "artist_name": artist_name,
            "audio_url": audio_url,
            "duration_text": duration_text,
            "track_image": track_image,
        }

    return None

def music(request, pk):
    """Страница плеера с информацией о треке"""
    track_details = get_track_details(pk)
    if not track_details:
        return render(request, "music.html", {"error": "Track not found"})
    return render(request, "music.html", track_details)


@login_required(login_url='login')
def index(request):
    artists_info = top_artists()
    top_track_list = top_tracks()

    first_six_tracks = top_track_list[:6]
    second_six_tracks = top_track_list[6:12]
    third_six_tracks = top_track_list[12:18]

    context = {
        'artists_info': artists_info,
        'first_six_tracks': first_six_tracks,  # Исправил название
        'second_six_tracks': second_six_tracks,
        'third_six_tracks': third_six_tracks,
    }

    return render(request, 'index.html', context)


def get_track_image(track_id):
    """Получает изображение трека с Deezer"""
    url = f"https://api.deezer.com/track/{track_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data.get("album", {}).get("cover_big", "")

    return ""


def search(request):
    if request.method == 'POST':
        search_query = request.POST.get('search_query', '')

        # Формируем URL для запроса к Deezer API
        url = f"https://api.deezer.com/search?q={search_query}"

        response = requests.get(url)

        track_list = []

        if response.status_code == 200:
            data = response.json()
            tracks = data.get("data", [])

            for track in tracks:
                track_name = track["title"]
                artist_name = track["artist"]["name"]
                duration = f"{track['duration'] // 60}:{track['duration'] % 60:02d}"
                trackid = track["id"]
                trackimage = track["album"]["cover_medium"]

                track_list.append({
                    'track_name': track_name,
                    'artist_name': artist_name,
                    'duration': duration,
                    'trackid': trackid,
                    'trackimage': trackimage,
                })

        context = {
            'search_results_count': len(track_list),
            'track_list': track_list,
        }
        return render(request, 'search.html', context)

    return render(request, 'search.html')


def profile(request, pk):
    """Отображает профиль артиста с топ-треками"""
    artist_id = pk
    url = f"{DEEZER_API_URL}/artist/{artist_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        name = data.get("name", "Unknown Artist")
        monthly_listeners = data.get("nb_fan", 0)
        header_url = data.get("picture_xl", "")

        # Получаем топ-треки артиста
        tracks_url = f"{DEEZER_API_URL}/artist/{artist_id}/top?limit=10"
        tracks_response = requests.get(tracks_url)

        top_tracks = []
        if tracks_response.status_code == 200:
            tracks_data = tracks_response.json().get("data", [])

            for track in tracks_data:
                track_id = str(track.get("id", ""))
                track_name = str(track.get("title", "Unknown Track"))
                track_image = get_track_image(track_id)

                duration = track.get("duration", 0)
                minutes = duration // 60
                seconds = duration % 60
                duration_text = f"{minutes}:{seconds:02d}"

                track_info = {
                    "id": track_id,
                    "name": track_name,
                    "durationText": duration_text,
                    "playCount": track.get("rank", 0),
                    "track_image": track_image,
                }
                top_tracks.append(track_info)

        artist_data = {
            "name": name,
            "monthlyListeners": monthly_listeners,
            "headerUrl": header_url,
            "topTracks": top_tracks,
        }
        return render(request, 'profile.html', artist_data)

    return render(request, 'profile.html', {"error": "Artist not found"})

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('/')
        else:
            messages.info(request, 'Invalid Credentials')
            return redirect('login')

    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email taken')
                return redirect('signup')
            elif User.objects.filter(username=username).exists():
                messages.info(request, 'Username taken')
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                # log user in
                user_login = auth.authenticate(username=username, password=password)
                auth.login(request, user_login)
                return redirect('/')
        else:
            messages.info(request, 'Passwords do not match')
            return redirect('signup')

    else:
        return render(request, 'signup.html')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    return redirect('login')
