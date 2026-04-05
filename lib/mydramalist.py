# -*- coding: utf-8 -*-
import re

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from bs4 import BeautifulSoup
from cloudscraper import create_scraper

MDL_BASE = 'https://mydramalist.com'

URLS = {
    'top_dramas':     MDL_BASE + '/shows/top?lang=pt-BR',
    'popular_dramas': MDL_BASE + '/shows/popular?lang=pt-BR',
    'top_movies':     MDL_BASE + '/movies/top?lang=pt-BR',
    'popular_movies': MDL_BASE + '/movies/popular?lang=pt-BR',
    'search_dramas':  MDL_BASE + '/search?q={query}&adv=titles&ty=68&lang=pt-BR',
    'search_movies':  MDL_BASE + '/search?q={query}&adv=titles&ty=77&lang=pt-BR',
}

HEADERS = {
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': MDL_BASE,
}

_scraper = create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
    delay=5,
)

def _get(url, timeout=30):
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None

def _soup(html):
    return BeautifulSoup(html, 'html.parser')

def _img(url, size='f'):
    if not url:
        return ''
    return re.sub(r'[a-z](\.[a-zA-Z]{3,4}(\?.*)?$)', size + r'\1', url)

def _year_from_info(info_text):
    m = re.search(r'\b(19|20)\d{2}\b', info_text or '')
    return m.group(0) if m else ''

def _parse_list_page(html_text):
    if not html_text:
        return []

    soup  = _soup(html_text)
    items = []

    for card in soup.select('div.box[id^="mdl-"]'):
        try:
            a_title = card.select_one('h6.title a')
            if not a_title:
                continue

            title = a_title.get_text(strip=True)
            href  = a_title.get('href', '')
            if not href.startswith('http'):
                href = MDL_BASE + href

            img_tag = card.select_one('img.cover')
            img     = _img(img_tag.get('data-src') or img_tag.get('src') or '') if img_tag else ''

            info_tag = card.select_one('span.text-muted')
            info     = info_tag.get_text(strip=True) if info_tag else ''
            year     = _year_from_info(info)

            score_tag = card.select_one('span.score')
            score     = score_tag.get_text(strip=True) if score_tag else ''

            description = ''
            for p in card.select('p'):
                txt = p.get_text(strip=True)
                if txt and score not in txt and len(txt) > 20:
                    description = txt
                    break

            if title:
                items.append((title, img, href, description, score, info, year))
        except Exception:
            continue

    return items

def _parse_search_page(html_text):
    if not html_text:
        return []

    soup  = _soup(html_text)
    items = []

    for item in soup.select('.result-item'):
        try:
            a_title = (
                item.select_one('.title a')
                or item.select_one('h6 a')
                or item.select_one('h2 a')
                or item.find('a')
            )
            if not a_title:
                continue

            title = a_title.get_text(strip=True)
            href  = a_title.get('href', '')
            if not href.startswith('http'):
                href = MDL_BASE + href

            img_tag = item.find('img')
            img     = _img(img_tag.get('data-src') or img_tag.get('src') or '') if img_tag else ''

            info_tag = item.select_one('.text-muted')
            info     = info_tag.get_text(strip=True) if info_tag else ''
            year     = _year_from_info(info)

            score_tag = item.select_one('.score')
            score     = score_tag.get_text(strip=True) if score_tag else ''

            description = ''
            for p in item.select('p'):
                txt = p.get_text(strip=True)
                if txt and score not in txt and len(txt) > 20:
                    description = txt
                    break

            if title:
                items.append((title, img, href, description, score, info, year))
        except Exception:
            continue

    return items if items else _parse_list_page(html_text)

def top_dramas(page=1):
    url = URLS['top_dramas'] + ('&page={}'.format(page) if page > 1 else '')
    return _parse_list_page(_get(url) or '')

def popular_dramas(page=1):
    url = URLS['popular_dramas'] + ('&page={}'.format(page) if page > 1 else '')
    return _parse_list_page(_get(url) or '')

def search_dramas(query):
    url = URLS['search_dramas'].format(query=quote_plus(query))
    return _parse_search_page(_get(url) or '')

def top_movies(page=1):
    url = URLS['top_movies'] + ('&page={}'.format(page) if page > 1 else '')
    return _parse_list_page(_get(url) or '')

def popular_movies(page=1):
    url = URLS['popular_movies'] + ('&page={}'.format(page) if page > 1 else '')
    return _parse_list_page(_get(url) or '')

def search_movies(query):
    url = URLS['search_movies'].format(query=quote_plus(query))
    return _parse_search_page(_get(url) or '')

def get_episodes(mdl_series_url):
    eps_url = mdl_series_url.rstrip('/') + '/episodes?lang=pt-BR'
    html    = _get(eps_url)
    if not html:
        return []

    soup     = _soup(html)
    episodes = []
    counter  = 0

    for ep_div in soup.select('div.episode'):
        try:
            counter += 1

            cover_div = ep_div.select_one('div.cover')
            img_tag   = cover_div.find('img') if cover_div else ep_div.find('img')
            img       = (img_tag.get('data-src') or img_tag.get('src') or '') if img_tag else ''

            a_tag   = ep_div.select_one('h2.title a') or ep_div.select_one('div.cover a') or ep_div.find('a')
            ep_href = a_tag.get('href', '') if a_tag else ''
            ep_num  = counter
            m = re.search(r'/episode/(\d+)', ep_href)
            if m:
                ep_num = int(m.group(1))

            raw   = a_tag.get_text(strip=True) if a_tag else ''
            m_ep  = re.search(r'(Episode\s+\d+.*)', raw)
            title = m_ep.group(1).strip() if m_ep else 'Episode {}'.format(ep_num)

            desc_div    = ep_div.select_one('div.summary')
            description = ''
            if desc_div:
                for a in desc_div.find_all('a'):
                    a.decompose()
                description = desc_div.get_text(' ', strip=True).strip()

            air_tag  = ep_div.select_one('.air-date')
            air_date = air_tag.get_text(strip=True) if air_tag else ''

            score_b  = ep_div.select_one('.rating-panel b')
            ep_score = score_b.get_text(strip=True) if score_b else ''

            episodes.append((ep_num, title, img, description, air_date, ep_score))

        except Exception:
            continue

    return episodes