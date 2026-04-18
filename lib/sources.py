import os
import sys
import re

try:
    import xbmcaddon
    if 'addonId' not in vars():
        addonId = re.search(r'plugin://(.+?)/', str(sys.argv[0])).group(1)
    addon_instance = xbmcaddon.Addon(id=addonId)
    addon_path = addon_instance.getAddonInfo('path')
    scrapers_path = os.path.join(addon_path, 'lib', 'scrapers')
except Exception:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    scrapers_path = os.path.join(dir_path, 'scrapers')
    addon_instance = None


def _is_enabled(script_name):
    if addon_instance is None:
        return True
    try:
        return addon_instance.getSetting('source_' + script_name) != 'false'
    except Exception:
        return True


def import_scripts(pasta):
    if not os.path.isdir(pasta):
        return []
    modulos = []
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    scripts = sorted(
        f[:-3] for f in os.listdir(pasta)
        if f.endswith('.py') and f != '__init__.py'
    )
    for script in scripts:
        if not _is_enabled(script):
            continue
        try:
            if sys.version_info.major == 3:
                import importlib
                modulo = (importlib.reload(sys.modules[script])
                          if script in sys.modules
                          else importlib.import_module(script))
            else:
                modulo = __import__(script)
            if hasattr(modulo, 'Source'):
                modulos.append(modulo)
        except Exception:
            pass
    return modulos


modules_import = import_scripts(scrapers_path)


def _label(modulo):
    return getattr(modulo, 'WEBSITE', modulo.__name__.replace('_', ' ').upper())


def show_content(title, mdl_id, episode):
    results = []
    for modulo in modules_import:
        site = _label(modulo)
        try:
            links = modulo.Source().tvshow(
                title=title,
                mdl_id=mdl_id,
                episode=int(episode),
            )
            for player_name, url in (links or []):
                results.append((f'{site} - {player_name}', url))
        except Exception:
            pass
    return results


def movie_content(title, mdl_id):
    results = []
    for modulo in modules_import:
        site = _label(modulo)
        try:
            links = modulo.Source().movie(title=title, mdl_id=mdl_id)
            for player_name, url in (links or []):
                results.append((f'{site} - {player_name}', url))
        except Exception:
            pass
    return results


def resolve_tvshows(url):
    stream = ''
    sub = ''
    for modulo in modules_import:
        if stream:
            break
        try:
            s, sb = modulo.Source().resolve_tvshows(url)
            if s:
                stream = s
                sub = sb or ''
        except Exception:
            pass
    return stream, sub


def resolve_movies(url):
    stream = ''
    sub = ''
    for modulo in modules_import:
        if stream:
            break
        try:
            s, sb = modulo.Source().resolve_movies(url)
            if s:
                stream = s
                sub = sb or ''
        except Exception:
            pass
    return stream, sub