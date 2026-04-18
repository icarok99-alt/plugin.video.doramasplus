import re
import requests
from bs4 import BeautifulSoup

try:
    from lib.resolver import Resolver
except ImportError:
    from resolver import Resolver

_resolver = Resolver()

WEBSITE = 'MY DORAMAS'

BASE_URL = 'https://www.mydoramas.net/'
SEARCH_URL = BASE_URL + 'search/?q={query}'

PRIMARY_CDN = 'https://ondemand.mylifekorea.shop'
FALLBACK_CDN = 'https://forks-doramas.mylifekorea.shop'

HEADERS = {
    'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8',
    'Referer':         BASE_URL,
}

_session = requests.Session()
_session.headers.update(HEADERS)

MDL_BASE = 'https://mydramalist.com/'


def _get(url, timeout=20):
    try:
        r = _session.get(url, timeout=timeout, allow_redirects=True)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def _soup(html):
    return BeautifulSoup(html, 'html.parser')


def _clean_title(title):
    if not title:
        return title
    cleaned = re.split(
        r'\s*[\-\u2013:]?\s*(?:'
        r'season\s*\d+'
        r'|\d+[aªo°]\s*temporada'
        r'|temporada\s*\d+'
        r'|part(?:e)?\s*\d+'
        r'|\bs\d+\b'
        r'|\b\d+\s*:'
        r')',
        title, maxsplit=1, flags=re.IGNORECASE,
    )[0].strip()
    cleaned = re.sub(r'\s*\((19|20)\d{2}\)\s*$', '', cleaned).strip()
    return cleaned or title


def _search_content(title, is_movie=False):
    if not title:
        return None
    try:
        url = SEARCH_URL.format(query=title.replace(' ', '+'))
        html = _get(url)
        if not html:
            return None
        soup = _soup(html)

        keywords = [kw for kw in re.findall(r'\w+', title.lower()) if len(kw) > 2]
        candidates = []

        for card in soup.select('.episode-card'):
            for a in card.select('a[href]'):
                href = a.get('href', '')
                if not href:
                    continue
                if is_movie and '/filmes/' not in href:
                    continue
                if not is_movie and '/series/' not in href and '/filmes/' not in href:
                    continue

                found_title = a.get_text(strip=True)
                if not found_title:
                    h3 = card.select_one('h3')
                    found_title = h3.get_text(strip=True) if h3 else ''
                if not found_title:
                    continue

                score = 0
                ft_lower = found_title.lower()
                tl_lower = title.lower()

                if tl_lower == ft_lower or ft_lower.startswith(tl_lower):
                    score += 150
                elif tl_lower in ft_lower:
                    score += 80

                for kw in keywords:
                    if kw in ft_lower:
                        score += 30

                if is_movie and '/filmes/' in href:
                    score += 60
                if not is_movie and '/series/' in href:
                    score += 40

                if score > 0:
                    if href.startswith('/'):
                        href = BASE_URL.rstrip('/') + href
                    candidates.append((score, found_title, href))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]

        pattern = r'/filmes/' if is_movie else r'/series/'
        first = soup.find('a', href=lambda h: h and re.search(pattern, h))
        if first:
            href = first['href']
            return BASE_URL.rstrip('/') + href if href.startswith('/') else href

    except Exception:
        pass
    return None


def _get_episode_url(series_url, season=1, episode=1):
    html = _get(series_url)
    if not html:
        return None
    soup = _soup(html)

    season_blocks = soup.select('.dorama-one-season-block')
    target_block = None

    for block in season_blocks:
        title_span = block.select_one('.dorama-one-season-title')
        if title_span:
            nums = re.findall(r'\d+', title_span.get_text())
            if nums and int(nums[0]) == season:
                target_block = block
                break

    if not target_block:
        idx = season - 1
        if 0 <= idx < len(season_blocks):
            target_block = season_blocks[idx]
        elif season_blocks:
            target_block = season_blocks[0]

    if not target_block:
        return None

    ep_list = target_block.select('.dorama-one-episode-list .dorama-one-episode-item')

    for a in ep_list:
        num_span = a.select_one('.dorama-one-episode-number')
        if num_span:
            nums = re.findall(r'\d+', num_span.get_text())
            if nums and int(nums[0]) == episode:
                href = a.get('href', '')
                if href:
                    return BASE_URL.rstrip('/') + href if href.startswith('/') else href

    if ep_list and 0 < episode <= len(ep_list):
        href = ep_list[episode - 1].get('href', '')
        if href:
            return BASE_URL.rstrip('/') + href if href.startswith('/') else href

    path = series_url.rstrip('/').split('mydoramas.net')[-1]
    slug = path.strip('/')
    return f'{BASE_URL}series/{slug}/temporada-{season}/episodio-{episode:02d}'


def _extract_urlconfig(html):
    m = re.search(r'var\s+urlConfig\s*=\s*\{([^}]+)\}', html)
    if not m:
        return None
    cfg = {}
    for key, value in re.findall(r'(\w+)\s*:\s*["\']?([^,"\'}\n]+)["\']?', m.group(1)):
        v = value.strip().strip('"\'')
        try:
            cfg[key] = int(v)
        except ValueError:
            cfg[key] = v
    return cfg if cfg else None


def _extract_cdn_urls(html):
    primary = PRIMARY_CDN
    fallback = FALLBACK_CDN

    m = re.search(r'const\s+PRIMARY_URL\s*=\s*["\']([^"\']+)["\']', html)
    if m:
        primary = m.group(1).strip()

    m = re.search(r'const\s+FALLBACK_URL\s*=\s*["\']([^"\']+)["\']', html)
    if m:
        fallback = m.group(1).strip()

    return primary, fallback


def _build_stream_url(cfg, cdn_url):
    slug = cfg.get('slug', '')
    tipo = cfg.get('tipo', 'doramas')
    pt = slug[0].upper() if slug else 'A'

    if tipo == 'filmes':
        path = f'{pt}/{slug}/stream/stream.m3u8'
    else:
        temp_num = str(cfg.get('temporada', 1)).zfill(2)
        ep_num = str(cfg.get('episodio', 1)).zfill(2)
        path = f'{pt}/{slug}/{temp_num}-temporada/{ep_num}/stream.m3u8'

    return f'{cdn_url.rstrip("/")}/{path}'


def _get_players(episode_url, title=""):
    players = []
    html = _get(episode_url)
    if not html:
        return players

    cfg = _extract_urlconfig(html)
    if not cfg:
        return players

    primary_url, fallback_url = _extract_cdn_urls(html)
    audio = detect_audio_type(title)

    primary_stream = _build_stream_url(cfg, primary_url)
    fallback_stream = _build_stream_url(cfg, fallback_url)

    try:
        r = _session.head(primary_stream, timeout=5, allow_redirects=True)
        stream = primary_stream if r.status_code < 400 else fallback_stream
    except Exception:
        stream = fallback_stream

    players.append((audio, stream))
    return players


def detect_audio_type(title):
    if not title:
        return 'dublado'
    if re.search(r'\blegendado\b', title, re.IGNORECASE):
        return 'legendado'
    return 'dublado'



def _get_english_title(mdl_id):
    if not mdl_id:
        return ''
    try:
        base = mdl_id if mdl_id.startswith('http') else MDL_BASE + mdl_id.lstrip('/')
        url = base.rstrip('/') + '?lang=en-US'
        r = _session.get(
            url,
            headers={**HEADERS, 'Accept-Language': 'en-US,en;q=0.9'},
            timeout=15,
            allow_redirects=True,
        )
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


class Source:

    def tvshow(self, title, mdl_id, episode, season=1):
        if not title:
            return []
        base_title = _clean_title(title)
        english = _clean_title(_get_english_title(mdl_id))
        series_url = _search_content(base_title) or (english and _search_content(english))
        if not series_url:
            return []
        ep_url = _get_episode_url(series_url, season=season, episode=episode)
        if not ep_url:
            return []
        return _get_players(ep_url, title=title)

    def movie(self, title, mdl_id):
        if not title:
            return []
        base_title = _clean_title(title)
        english = _clean_title(_get_english_title(mdl_id))
        movie_url = _search_content(base_title, is_movie=True) or (english and _search_content(english, is_movie=True))
        if not movie_url:
            return []
        return _get_players(movie_url, title=title)

    def resolve_tvshows(self, url):
        try:
            stream, sub = _resolver.resolverurls(url, url)
            return stream, sub
        except Exception:
            return None, None

    def resolve_movies(self, url):
        return self.resolve_tvshows(url)