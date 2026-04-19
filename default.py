# -*- coding: utf-8 -*-
from lib.helper import *
import xbmc
from lib import mydramalist, sources, db
from lib.player import get_player
from lib.loading_manager import loading_manager
from lib.db_manager import DoramasDatabaseManager

DoramasDatabaseManager().check_auto_expiry()

if not exists(profile):
    try: os.makedirs(profile)
    except OSError as e:
        if e.errno != 17: pass

try:
    class Donate_(xbmcgui.WindowDialog):
        def __init__(self):
            try:
                self.image = xbmcgui.ControlImage(440, 128, 400, 400, translate(os.path.join(homeDir, 'resources', 'images', 'qrcode-pix.png')))
                self.text  = xbmcgui.ControlLabel(x=210, y=570, width=1100, height=25, label='[B][COLOR pink]SE ESSE ADD-ON LHE AGRADA, FAÇA UMA DOAÇÃO VIA PIX ACIMA E MANTENHA ESSE SERVIÇO ATIVO[/COLOR][/B]', textColor='pink')
                self.text2 = xbmcgui.ControlLabel(x=495, y=600, width=1000, height=25, label='[B][COLOR pink]PRESSIONE VOLTAR PARA SAIR[/COLOR][/B]', textColor='pink')
                self.addControl(self.image)
                self.addControl(self.text)
                self.addControl(self.text2)
            except: pass
except: pass


def donate_question():
    q = yesno('', 'Deseja fazer uma doação ao desenvolvedor?', nolabel='NÃO', yeslabel='SIM')
    if q:
        dialog2('AVISO', 'A DOAÇÃO É UMA AJUDA AO DESENVOLVEDOR PARA MANTER O ADD-ON ATIVO!')
        dialog_donate = Donate_()
        dialog_donate.doModal()


def _autoplay_order(players):
    pref = getsetting('autoplay_pref')
    first = 'dublado' if pref == '0' else 'legendado'
    second = 'legendado' if pref == '0' else 'dublado'
    pref_ = [i for i, (n, u) in enumerate(players) if first in n.lower()]
    fall_ = [i for i, (n, u) in enumerate(players) if second in n.lower()]
    other_ = [i for i in range(len(players)) if i not in pref_ and i not in fall_]
    return pref_ + fall_ + other_


@route('/')
def index():
    setcontent('videos')
    addMenuItem({'name': 'FILMES', 'description': '[B]Filmes asiáticos legendados e dublados - ação, romance, terror, fantasia e muito mais.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'movies.jpg'))}, destiny='/menu_filmes')
    addMenuItem({'name': 'DORAMAS', 'description': '[B]Séries asiáticas legendadas e dubladas - doramas coreanos, japoneses, chineses e muito mais.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'doramas.jpg'))}, destiny='/menu_doramas')
    addMenuItem({'name': 'CONFIGURAÇÕES', 'description': '[B]Ative a reprodução automática ou atualize o ResolveURL para manter os players funcionando.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'settings.jpg'))}, destiny='/settings')
    addMenuItem({'name': 'DOAÇÃO', 'description': '[B]Gostou do add-on? Ajude o desenvolvedor a mantê-lo ativo com uma doação via PIX.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'donate.jpg'))}, destiny='/donate')
    end()


@route('/settings')
def settings(param=None):
    addon.openSettings()


@route('/donate')
def donate(param=None):
    donate_question()


@route('/menu_doramas')
def menu_doramas(param=None):
    setcontent('videos')
    addMenuItem({'name': 'PESQUISAR DORAMA', 'description': '[B]Digite o nome do dorama e encontre rapidamente a série que você procura.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'search.jpg'))}, destiny='/search_doramas')
    addMenuItem({'name': 'DORAMAS EM ALTA', 'description': '[B]Os doramas com as maiores notas - os queridinhos da audiência asiática.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'trending.jpg'))}, destiny='/doramas_top')
    addMenuItem({'name': 'DORAMAS POPULARES', 'description': '[B]Os doramas mais populares no momento - veja o que todo mundo está assistindo.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'popular.jpg'))}, destiny='/doramas_popular')
    end()


@route('/menu_filmes')
def menu_filmes(param=None):
    setcontent('videos')
    addMenuItem({'name': 'PESQUISAR FILME', 'description': '[B]Digite o nome do filme e encontre rapidamente o que você procura.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'search.jpg'))}, destiny='/search_filmes')
    addMenuItem({'name': 'FILMES EM ALTA', 'description': '[B]Os filmes asiáticos com as maiores notas - as melhores produções do cinema oriental.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'trending.jpg'))}, destiny='/filmes_top')
    addMenuItem({'name': 'FILMES POPULARES', 'description': '[B]Os filmes asiáticos mais populares no momento - veja o que todo mundo está assistindo.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'popular.jpg'))}, destiny='/filmes_popular')
    end()


def _render_dramas(items, page, next_destiny):
    if not items:
        notify('Nenhum item disponível')
        return
    setcontent('tvshows')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'title': title, 'year': year}, destiny='/open_episodes_mdl')
    addMenuItem({'name': 'Próxima página', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'next.jpg')), 'page': page + 1}, destiny=next_destiny)
    end()


def _render_movies(items, page, next_destiny):
    if not items:
        notify('Nenhum item disponível')
        return
    setcontent('movies')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'title': title, 'year': year, 'playable': True}, destiny='/play_filme', folder=False)
    addMenuItem({'name': 'Próxima página', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'next.jpg')), 'page': page + 1}, destiny=next_destiny)
    end()


@route('/doramas_top')
def doramas_top(param=None):
    page = int(param.get('page', 1)) if param else 1
    _render_dramas(mydramalist.top_dramas(page), page, '/doramas_top')


@route('/doramas_popular')
def doramas_popular(param=None):
    page = int(param.get('page', 1)) if param else 1
    _render_dramas(mydramalist.popular_dramas(page), page, '/doramas_popular')


@route('/search_doramas')
def search_doramas(param=None):
    keyboard = xbmc.Keyboard('', 'Pesquisar Dorama')
    keyboard.doModal()
    if not keyboard.isConfirmed() or not (query := keyboard.getText().strip()): return
    items = mydramalist.search_dramas(query)
    if not items:
        notify('Nenhum resultado encontrado')
        return
    setcontent('tvshows')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'title': title, 'year': year}, destiny='/open_episodes_mdl')
    end()


@route('/filmes_top')
def filmes_top(param=None):
    page = int(param.get('page', 1)) if param else 1
    _render_movies(mydramalist.top_movies(page), page, '/filmes_top')


@route('/filmes_popular')
def filmes_popular(param=None):
    page = int(param.get('page', 1)) if param else 1
    _render_movies(mydramalist.popular_movies(page), page, '/filmes_popular')


@route('/search_filmes')
def search_filmes(param=None):
    keyboard = xbmc.Keyboard('', 'Pesquisar Filme')
    keyboard.doModal()
    if not keyboard.isConfirmed() or not (query := keyboard.getText().strip()): return
    items = mydramalist.search_movies(query)
    if not items:
        notify('Nenhum resultado encontrado')
        return
    setcontent('movies')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'title': title, 'year': year, 'playable': True}, destiny='/play_filme', folder=False)
    end()


@route('/open_episodes_mdl')
def open_episodes_mdl(param):
    serie_title = param.get('title', param.get('name', ''))
    serie_img = param.get('iconimage', '')
    mdl_id = param.get('url', '')
    year = param.get('year', '')
    if not mdl_id:
        notify('URL inválida')
        return
    episodes = mydramalist.get_episodes(mdl_id)
    if not episodes:
        notify('Nenhum episódio encontrado')
        return
    watched_set = db.get_watched(mdl_id)
    setcontent('episodes')
    for ep_num, ep_title, ep_img, ep_desc, air_date, ep_score in episodes:
        label = f'[COLOR gold]★ {ep_score}[/COLOR]  {ep_title}' if ep_score else ep_title
        desc = '\n'.join(filter(None, [air_date, ep_desc]))
        addMenuItem({'name': label, 'description': desc, 'iconimage': ep_img or serie_img,
                     'serie_title': serie_title, 'episode_num': str(ep_num),
                     'episode_title': ep_title, 'year': year, 'mdl_id': mdl_id,
                     'playable': True, 'playcount': 1 if ep_num in watched_set else 0},
                    destiny='/play_dorama', folder=False)
    end()


@route('/play_dorama')
def play_dorama(param):
    serie_title = param.get('serie_title', '')
    episode_num = int(param.get('episode_num', 1))
    episode_title = param.get('episode_title', '')
    iconimage = param.get('iconimage', '')
    fanart = param.get('fanart', '')
    description = param.get('description', '')
    year = param.get('year', '')
    mdl_id = param.get('mdl_id', '')

    loading_manager.show()

    players = sources.show_content(title=serie_title, mdl_id=mdl_id, episode=episode_num)
    if not players:
        loading_manager.force_close()
        notify('Nenhum player encontrado')
        return

    if getsetting('autoplay') == 'true':
        order = _autoplay_order(players)
        loading_manager.set_resolving()
    else:
        idx = loading_manager.set_phase2([(n, '') for n, u in players])
        if idx < 0:
            loading_manager.force_close()
            return
        order = [idx] + [i for i in range(len(players)) if i != idx]

    stream = None
    for i in order:
        name, player_url = players[i]
        if not player_url: continue
        try:
            stream, _ = sources.resolve_tvshows(player_url)
            if stream: break
        except:
            continue

    if not stream:
        loading_manager.force_close()
        notify('STREAM INDISPONÍVEL')
        return

    # Parsear URL e headers do stream (formato: url|Header=valor&Header2=valor2)
    if '|' in stream:
        url, raw_headers = stream.split('|', 1)
    else:
        url, raw_headers = stream, ''

    play_item = xbmcgui.ListItem(label=episode_title or serie_title, path=url)
    play_item.setArt({'thumb': iconimage, 'icon': iconimage, 'fanart': fanart or iconimage})
    play_item.setContentLookup(False)

    # Detectar tipo de manifest e configurar inputstream.adaptive
    url_lower = url.lower().split('?')[0]
    if '.m3u8' in url_lower:
        play_item.setMimeType('application/vnd.apple.mpegurl')
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    elif '.mpd' in url_lower:
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    else:
        play_item.setMimeType('video/mp4')

    # Repassar headers ao inputstream.adaptive (stream + manifest)
    if raw_headers:
        play_item.setProperty('inputstream.adaptive.stream_headers', raw_headers)
        play_item.setProperty('inputstream.adaptive.manifest_headers', raw_headers)

    kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    if kodi_version >= 20:
        tag = play_item.getVideoInfoTag()
        tag.setTitle(episode_title or serie_title)
        tag.setPlot(description)
        tag.setMediaType('episode')
        if year and year != '0':
            try: tag.setYear(int(year))
            except: pass
        tag.setTvShowTitle(serie_title)
        tag.setOriginalTitle(serie_title)
        tag.setSeason(1)
        tag.setEpisode(episode_num)
    else:
        info = {'title': episode_title or serie_title, 'plot': description, 'mediatype': 'episode', 
                'tvshowtitle': serie_title, 'originaltitle': serie_title, 'season': 1, 'episode': episode_num}
        if year and year != '0':
            try: info['year'] = int(year)
            except: pass
        play_item.setInfo('video', info)

    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, play_item)
    loading_manager.close()

    # Playlist simples direta
    if mdl_id:
        try:
            episodes = db.get_episodes(mdl_id)
            if episodes:
                playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                kv = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
                addon_id = plugin.split('/')[2]
                for ep in episodes:
                    ep_num = ep.get('ep_num', 0)
                    if ep_num <= episode_num: continue
                    ep_title = ep.get('ep_title') or f'Episode {ep_num}'
                    ep_img = ep.get('ep_img') or iconimage
                    params = {'serie_title': serie_title, 'episode_num': str(ep_num), 'episode_title': ep_title, 
                              'iconimage': ep_img, 'description': ep.get('ep_desc', ''), 'mdl_id': mdl_id}
                    from urllib.parse import urlencode, quote_plus
                    purl = f'plugin://{addon_id}/play_dorama/{quote_plus(urlencode(params))}'
                    li = xbmcgui.ListItem(ep_title)
                    li.setArt({'thumb': ep_img, 'icon': ep_img})
                    if kv >= 20:
                        tag = li.getVideoInfoTag()
                        tag.setTitle(ep_title)
                        tag.setTvShowTitle(serie_title)
                        tag.setMediaType('episode')
                        tag.setEpisode(ep_num)
                    else:
                        li.setInfo('video', {'title': ep_title, 'tvshowtitle': serie_title, 'mediatype': 'episode', 'episode': ep_num})
                    playlist.add(url=purl, listitem=li)
        except:
            pass

        next_ep = db.get_next_episode(mdl_id, episode_num)
        next_info = {'ep_num': next_ep['ep_num'], 'ep_title': next_ep.get('ep_title', ''), 'ep_img': next_ep.get('ep_img', '')} if next_ep else None
        get_player().start_monitoring(mdl_id, episode_num, serie_title, next_info)


@route('/play_filme')
def play_filme(param):
    title = param.get('title', param.get('name', ''))
    iconimage = param.get('iconimage', '')
    fanart = param.get('fanart', '')
    description = param.get('description', '')
    year = param.get('year', '')

    loading_manager.show()

    players = sources.movie_content(title=title, mdl_id=param.get('url', ''))
    if not players:
        loading_manager.force_close()
        notify('Nenhum player encontrado')
        return

    if getsetting('autoplay') == 'true':
        order = _autoplay_order(players)
        loading_manager.set_resolving()
    else:
        idx = loading_manager.set_phase2([(n, '') for n, u in players])
        if idx < 0:
            loading_manager.force_close()
            return
        order = [idx] + [i for i in range(len(players)) if i != idx]

    stream = None
    for i in order:
        name, player_url = players[i]
        if not player_url: continue
        try:
            stream, _ = sources.resolve_movies(player_url)
            if stream: break
        except:
            continue

    if not stream:
        loading_manager.force_close()
        notify('STREAM INDISPONÍVEL')
        return

    # Parsear URL e headers do stream (formato: url|Header=valor&Header2=valor2)
    if '|' in stream:
        url, raw_headers = stream.split('|', 1)
    else:
        url, raw_headers = stream, ''

    play_item = xbmcgui.ListItem(label=title, path=url)
    play_item.setArt({'thumb': iconimage, 'icon': iconimage, 'fanart': fanart or iconimage})
    play_item.setContentLookup(False)

    # Detectar tipo de manifest e configurar inputstream.adaptive
    url_lower = url.lower().split('?')[0]
    if '.m3u8' in url_lower:
        play_item.setMimeType('application/vnd.apple.mpegurl')
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    elif '.mpd' in url_lower:
        play_item.setMimeType('application/dash+xml')
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    else:
        play_item.setMimeType('video/mp4')

    # Repassar headers ao inputstream.adaptive (stream + manifest)
    if raw_headers:
        play_item.setProperty('inputstream.adaptive.stream_headers', raw_headers)
        play_item.setProperty('inputstream.adaptive.manifest_headers', raw_headers)

    kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    if kodi_version >= 20:
        tag = play_item.getVideoInfoTag()
        tag.setTitle(title)
        tag.setPlot(description)
        tag.setMediaType('movie')
        if year and year != '0':
            try: tag.setYear(int(year))
            except: pass
        tag.setOriginalTitle(title)
    else:
        info = {'title': title, 'plot': description, 'mediatype': 'movie', 'originaltitle': title}
        if year and year != '0':
            try: info['year'] = int(year)
            except: pass
        play_item.setInfo('video', info)

    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, play_item)
    loading_manager.close()