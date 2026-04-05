import re
import base64
import json
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup
import cloudscraper

BASE_URL = 'https://doramasonline.org/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8',
    'Referer': BASE_URL,
}

_scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
    delay=5,
)

def _get(url, timeout=20):
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        return None

def _soup(html):
    return BeautifulSoup(html, 'html.parser')

def _clean_url(url):
    if not url:
        return url

    original = url[:300]

    try:
        cleaned = url.strip()

        if 'q1n.net/off/?url=' in cleaned:
            cleaned = cleaned.split('q1n.net/off/?url=')[1]
            cleaned = unquote(cleaned.split('&')[0])

        elif 'rogeriobetin.com' in cleaned:
            if '/noance/?' in cleaned:
                part = cleaned.split('/noance/?')[1]
                cleaned = 'https://rogeriobetin.com/noance/?' + unquote(part.split('&')[0] if '&' in part else part)

        if any(x in cleaned for x in ['/off/?url=', '/out/?url=', '/go/?url=']):
            for param in ['/off/?url=', '/out/?url=', '/go/?url=']:
                if param in cleaned:
                    cleaned = unquote(cleaned.split(param)[-1].split('&')[0])
                    break

        dirty = ['&img=', '&poster=', '&token=', '&expires=', '&signature=', '&type=', 
                 '&sub=', '&lang=', '&referer=', '&domain=', '&t=', '&v=', '&player=', '&amp;']

        for d in dirty:
            if d in cleaned:
                cleaned = cleaned.split(d)[0]

        cleaned = cleaned.rstrip('&?')

        return cleaned.strip()

    except Exception as e:
        return url.strip()

def _decode_holuagency(url):
    try:
        return _clean_url(url)
    except:
        return url.strip()

def _get_players(page_url):
    players = []
    try:
        html = _get(page_url)
        if not html:
            return players

        soup = _soup(html)
        nomes_por_nume = {}

        for li in soup.select('ul#playeroptionsul li.dooplay_player_option'):
            nume = li.get('data-nume', '').strip()
            name_tag = li.find('span', class_='title')
            name = name_tag.text.strip() if name_tag else f'Opção {nume}'
            if nume:
                nomes_por_nume[nume] = name

        for box in soup.select('#dooplay_player_content .source-box'):
            box_id = box.get('id', '')
            m = re.search(r'source-player-(\d+)', box_id)
            nume = m.group(1) if m else None
            name = nomes_por_nume.get(nume, f'Opção {nume}') if nume else 'Player'

            a = box.find('a', href=True)
            if a and a.get('href'):
                players.append((name, _decode_holuagency(a['href'].strip())))
                continue

            iframe = box.find('iframe', src=True)
            if iframe and iframe.get('src'):
                players.append((name, _decode_holuagency(iframe['src'].strip())))

        if not players:
            for i, iframe in enumerate(soup.find_all('iframe', src=True), 1):
                players.append((f'Player {i}', _decode_holuagency(iframe.get('src', ''))))

    except Exception:
        pass
    return players

def _search_serie(title):
    if not title:
        return None
    try:
        search_url = BASE_URL + '?s=' + title.replace(' ', '+')
        html = _get(search_url)
        if not html:
            return None

        soup = _soup(html)
        candidates = []
        keywords = re.findall(r'\w+', title.lower())

        for item in soup.find_all(['div', 'article'], class_=lambda x: x and any(c in (x or '') for c in ['result-item', 'post', 'item'])):
            a = item.find('a', href=True)
            if not a: continue
            href = a.get('href', '')
            title_tag = item.find(['h3', 'div.title', 'h2']) or a
            found_title = title_tag.get_text(strip=True) if title_tag else ''

            if not found_title or any(x in found_title.lower() for x in ['related', 'recomendado', 'sugestão', 'sequel', 'season 2', 'temporada 2']):
                continue

            score = 90 if any(x in found_title.lower() for x in ['class 1', 'season 1', 'temporada 1']) else 0
            if title.lower() in found_title.lower() or found_title.lower().startswith(title.lower()):
                score += 100
            else:
                for kw in keywords:
                    if len(kw) > 3 and kw in found_title.lower():
                        score += 25

            if score > 0:
                candidates.append((score, found_title, href))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]

        first = soup.find('a', href=lambda h: h and ('/serie/' in h or '/series/' in h or '/temporada/' in h or '/filme/' in h))
        if first:
            return first['href']
    except:
        pass
    return None

class VOD:
    def tvshow(self, title=None, fallback='', season=1, episode=1):
        if not title:
            return []
        serie_url = _search_serie(title) or (fallback and _search_serie(fallback))
        if not serie_url:
            return []

        html = _get(serie_url)
        if not html:
            return []

        soup = _soup(html)
        episodios = soup.select('ul.episodios li, div.episodios li')
        target = None

        for li in episodios:
            num = li.select_one('.numerando')
            if num:
                txt = num.get_text(strip=True)
                if re.search(rf'\b0*{episode}\b', txt) or f'Ep {episode}' in txt:
                    a = li.select_one('a')
                    if a:
                        target = a.get('href')
                        break

        if not target:
            try:
                target = episodios[episode-1].select_one('a')['href']
            except:
                return []

        return _get_players(target)

    def movie(self, title=None, fallback=''):
        if not title:
            return []
        movie_url = _search_serie(title) or (fallback and _search_serie(fallback))
        if not movie_url:
            return []
        return _get_players(movie_url)