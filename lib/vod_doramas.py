import re
import base64
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
    except Exception:
        return None

def _soup(html):
    return BeautifulSoup(html, 'html.parser')

def _clean_url(url):
    if not url:
        return url
    try:
        cleaned = url.strip()
        if 'q1n.net/off/?url=' in cleaned:
            cleaned = unquote(cleaned.split('q1n.net/off/?url=')[1].split('&')[0])
        elif 'rogeriobetin.com' in cleaned:
            if '/noance/?' in cleaned:
                part = cleaned.split('/noance/?')[1]
                cleaned = 'https://rogeriobetin.com/noance/?' + unquote(part.split('&')[0] if '&' in part else part)
        for param in ['/off/?url=', '/out/?url=', '/go/?url=']:
            if param in cleaned:
                cleaned = unquote(cleaned.split(param)[-1].split('&')[0])
                break
        dirty = ['&img=', '&poster=', '&token=', '&expires=', '&signature=', '&type=',
                 '&sub=', '&lang=', '&referer=', '&domain=', '&t=', '&v=', '&player=', '&amp;']
        for d in dirty:
            if d in cleaned:
                cleaned = cleaned.split(d)[0]
        return cleaned.rstrip('&?').strip()
    except Exception:
        return url.strip()

def _decode_holuagency(url):
    if not url:
        return url
    try:
        cleaned = url.strip()
        if 'holuagency' not in cleaned:
            return _clean_url(cleaned)
        parsed = urlparse(cleaned)
        qs = parse_qs(parsed.query)
        if 'url' in qs:
            inner = unquote(qs['url'][0])
            try:
                decoded = base64.b64decode(inner + '==').decode('utf-8', errors='ignore')
                if decoded.startswith('http'):
                    return _clean_url(decoded)
            except Exception:
                pass
            if inner.startswith('http'):
                return _clean_url(inner)
        for segment in parsed.path.strip('/').split('/'):
            if len(segment) > 20:
                try:
                    padding = segment + '=' * (-len(segment) % 4)
                    decoded = base64.b64decode(padding).decode('utf-8', errors='ignore')
                    if decoded.startswith('http'):
                        return _clean_url(decoded)
                except Exception:
                    pass
        match = re.search(r'https?://(?!holuagency)[^\s&"\']+', cleaned)
        if match:
            return _clean_url(match.group(0))
        return _clean_url(cleaned)
    except Exception:
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
            name_lower = name.lower()
            if 'trailer' in name_lower or 'youtube' in name_lower or 'preview' in name_lower:
                continue
            a = box.find('a', href=True)
            if a and a.get('href'):
                url = _decode_holuagency(a['href'])
                if url:
                    url_lower = url.lower()
                    if 'youtube' in url_lower or 'trailer' in url_lower:
                        continue
                    players.append((name, url))
                continue
            iframe = box.find('iframe', src=True)
            if iframe and iframe.get('src'):
                url = _decode_holuagency(iframe['src'])
                if url:
                    url_lower = url.lower()
                    if 'youtube' in url_lower or 'trailer' in url_lower:
                        continue
                    players.append((name, url))
        if not players:
            for i, iframe in enumerate(soup.find_all('iframe', src=True), 1):
                url = _decode_holuagency(iframe.get('src', ''))
                if url:
                    url_lower = url.lower()
                    if 'youtube' not in url_lower and 'trailer' not in url_lower:
                        players.append((f'Player {i}', url))
    except Exception:
        pass
    return players

def _search_content(title, is_movie=False):
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
            if not a:
                continue
            href = a.get('href', '')
            title_tag = item.find(['h3', 'div.title', 'h2']) or a
            found_title = title_tag.get_text(strip=True) if title_tag else ''
            if not found_title:
                continue
            if any(x in found_title.lower() for x in ['related', 'recomendado', 'sugestão', 'sequel', 'temporada 2']):
                continue
            score = 0
            if title.lower() in found_title.lower() or found_title.lower().startswith(title.lower()):
                score += 120
            for kw in keywords:
                if len(kw) > 3 and kw in found_title.lower():
                    score += 35
            if is_movie:
                if any(x in href.lower() for x in ['/filmes/', '/filme/']):
                    score += 80
                if any(x in found_title.lower() for x in ['filme', 'movie']):
                    score += 40
            if score > 0:
                candidates.append((score, found_title, href))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]
        selector = '/filmes/' if is_movie else '/serie/|/series/|/temporada/'
        first = soup.find('a', href=lambda h: h and re.search(selector, h))
        if first:
            return first['href']
    except Exception:
        pass
    return None

MDL_BASE = 'https://mydramalist.com/'

def _get_english_title(mdl_id):
    if not mdl_id:
        return ''
    try:
        url = f'{MDL_BASE}{mdl_id.lstrip("/")}?lang=en-US'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        r = _scraper.get(url, headers=headers, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return ''
        soup = BeautifulSoup(r.text, 'html.parser')
        h1 = soup.select_one('h1.film-title, h1[itemprop="name"]')
        if h1:
            return h1.get_text(strip=True)
        t = soup.find('title')
        if t:
            return t.get_text(strip=True).split('|')[0].strip()
    except Exception:
        pass
    return ''

def _clean_title(title):
    if not title:
        return title
    cleaned = re.split(
        r'\s*[\-\u2013:]?\s*(?:'
        r'season\s*\d+'
        r'|\d+[aª°]\s*temporada'
        r'|temporada\s*\d+'
        r'|part(?:e)?\s*\d+'
        r'|\bs\d+\b'
        r'|\b\d+\s*:'
        r')',
        title, maxsplit=1, flags=re.IGNORECASE,
    )[0].strip()
    return cleaned or title


class VOD:
    def tvshow(self, title=None, mdl_id='', season=1, episode=1):
        if not title:
            return []
        english = _clean_title(_get_english_title(mdl_id))
        base_title = _clean_title(title)
        serie_url = _search_content(base_title) or (english and _search_content(english))
        if not serie_url:
            return []
        html = _get(serie_url)
        if not html:
            return []
        soup = _soup(html)
        target = None
        season_block = None
        for se_c in soup.select('div.se-c'):
            se_t = se_c.select_one('span.se-t')
            if se_t and se_t.get_text(strip=True) == str(season):
                season_block = se_c
                break
        episodios = (
            season_block.select('ul.episodios li')
            if season_block
            else soup.select('ul.episodios li, div.episodios li')
        )
        for li in episodios:
            num_div = li.select_one('.numerando')
            if not num_div:
                continue
            txt = num_div.get_text(strip=True)
            m = re.match(r'(\d+)\s*[-–]\s*(\d+)', txt)
            if m:
                if int(m.group(1)) == season and int(m.group(2)) == episode:
                    a = li.select_one('a')
                    if a:
                        target = a.get('href')
                        break
            elif re.fullmatch(rf'\s*0*{episode}\s*', txt):
                a = li.select_one('a')
                if a:
                    target = a.get('href')
                    break
        if not target:
            try:
                target = episodios[episode - 1].select_one('a')['href']
            except Exception:
                return []
        return _get_players(target)

    def movie(self, title=None, mdl_id=''):
        if not title:
            return []
        english = _clean_title(_get_english_title(mdl_id))
        base_title = _clean_title(title)
        movie_url = _search_content(base_title, is_movie=True) or (english and _search_content(english, is_movie=True))
        if not movie_url:
            return []
        return _get_players(movie_url)