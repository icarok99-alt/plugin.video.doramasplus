# -*- coding: utf-8 -*-
from lib.helper import *
from lib import mydramalist, vod_doramas
from lib.resolver import Resolver
from lib.proxy import get_proxy

if not exists(profile):
    try:
        os.makedirs(profile)
    except OSError as e:
        if e.errno != 17:
            pass

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
            except:
                pass
except:
    pass

def donate_question():
    q = yesno('', 'Deseja fazer uma doação ao desenvolvedor?', nolabel='NÃO', yeslabel='SIM')
    if q:
        dialog2('AVISO', 'A DOAÇÃO É UMA AJUDA AO DESENVOLVEDOR PARA MANTER O ADD-ON ATIVO!')
        dialog_donate = Donate_()
        dialog_donate.doModal()

resolver = Resolver()

def _autoplay_order(players):
    pref = getsetting('autoplay_pref')
    first  = 'dublado'   if pref == '0' else 'legendado'
    second = 'legendado' if pref == '0' else 'dublado'
    preferred = [i for i, (nome, url) in enumerate(players) if first  in nome.lower()]
    fallback  = [i for i, (nome, url) in enumerate(players) if second in nome.lower()]
    others    = [i for i in range(len(players)) if i not in preferred and i not in fallback]
    return preferred + fallback + others

def _play(result, title, iconimage, fanart, description, media_type, season=None, episode=None, serie_name='', original_name='', year=''):
    if not result:
        notify('STREAM INDISPONÍVEL')
        return

    sub = ''
    if '|sub=' in result:
        result, sub = result.split('|sub=', 1)

    proxy = get_proxy()
    if proxy:
        play_url = proxy.get_proxy_url(result)
    else:
        play_url = result.split('|')[0] if '|' in result else result

    play_item = xbmcgui.ListItem(label=title, path=play_url)
    play_item.setArt({'thumb': iconimage, 'icon': iconimage, 'fanart': fanart or iconimage})
    play_item.setContentLookup(False)
    play_item.setMimeType('video/mp4')

    if sub:
        play_item.setSubtitles([sub])

    kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    if kodi_version >= 20:
        tag = play_item.getVideoInfoTag()
        tag.setTitle(title)
        tag.setPlot(description)
        tag.setMediaType(media_type)
        if year and year != '0':
            try: tag.setYear(int(year))
            except: pass
        if media_type == 'episode':
            tag.setTvShowTitle(serie_name)
            tag.setOriginalTitle(original_name)
            if season: tag.setSeason(int(season))
            if episode: tag.setEpisode(int(episode))
        elif media_type == 'movie':
            tag.setOriginalTitle(original_name)
    else:
        info = {'title': title, 'plot': description, 'mediatype': media_type}
        if year and year != '0':
            try: info['year'] = int(year)
            except: pass
        if media_type == 'episode':
            info.update({'tvshowtitle': serie_name, 'originaltitle': original_name, 'season': int(season or 1), 'episode': int(episode or 1)})
        elif media_type == 'movie':
            info['originaltitle'] = original_name
        play_item.setInfo('video', info)

    notify('INICIANDO REPRODUÇÃO...')
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, play_item)

@route('/')
def index():
    setcontent('videos')
    addMenuItem({'name': 'DORAMAS', 'description': '[B]Séries asiáticas legendadas e dubladas — doramas coreanos, japoneses, chineses e muito mais.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'doramas.jpg'))}, destiny='/menu_doramas')
    addMenuItem({'name': 'FILMES', 'description': '[B]Filmes asiáticos legendados e dublados — ação, romance, terror, fantasia e muito mais.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'movies.jpg'))}, destiny='/menu_filmes')
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
    addMenuItem({'name': 'DORAMAS EM ALTA', 'description': '[B]Os doramas com as maiores notas — os queridinhos da audiência asiática.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'trending.jpg'))}, destiny='/doramas_top')
    addMenuItem({'name': 'DORAMAS POPULARES', 'description': '[B]Os doramas mais acessados no momento — veja o que todo mundo está assistindo.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'popular.jpg'))}, destiny='/doramas_popular')
    end()

@route('/menu_filmes')
def menu_filmes(param=None):
    setcontent('videos')
    addMenuItem({'name': 'PESQUISAR FILME', 'description': '[B]Digite o nome do filme e encontre rapidamente o que você procura.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'search.jpg'))}, destiny='/search_filmes')
    addMenuItem({'name': 'FILMES EM ALTA', 'description': '[B]Os filmes asiáticos com as maiores notas — as melhores produções do cinema oriental.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'trending.jpg'))}, destiny='/filmes_top')
    addMenuItem({'name': 'FILMES POPULARES', 'description': '[B]Os filmes asiáticos mais acessados no momento — veja o que está em alta.[/B]', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'popular.jpg'))}, destiny='/filmes_popular')
    end()

def _mdl_id(url):
    import re as _re
    m = _re.search(r'/(\d+)-', url or '')
    return m.group(1) if m else ''

def _render_dramas(items, page, next_destiny):
    if not items:
        notify('Nenhum item disponível')
        return
    setcontent('tvshows')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score:
            label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'mdl_id': _mdl_id(url), 'title': title, 'year': year}, destiny='/open_episodes_mdl')
    addMenuItem({'name': 'Próxima página', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'next.jpg')), 'page': page + 1}, destiny=next_destiny)
    end()

def _render_movies(items, page, next_destiny):
    if not items:
        notify('Nenhum item disponível')
        return
    setcontent('movies')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score:
            label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'mdl_id': _mdl_id(url), 'title': title, 'year': year, 'playable': True}, destiny='/play_filme', folder=False)
    addMenuItem({'name': 'Próxima página', 'iconimage': translate(os.path.join(homeDir, 'resources', 'images', 'next.jpg')), 'page': page + 1}, destiny=next_destiny)
    end()

@route('/doramas_top')
def doramas_top(param=None):
    page = int(param.get('page', 1)) if param else 1
    items = mydramalist.top_dramas(page)
    _render_dramas(items, page, '/doramas_top')

@route('/doramas_popular')
def doramas_popular(param=None):
    page = int(param.get('page', 1)) if param else 1
    items = mydramalist.popular_dramas(page)
    _render_dramas(items, page, '/doramas_popular')

@route('/search_doramas')
def search_doramas(param=None):
    keyboard = xbmc.Keyboard('', 'Pesquisar Dorama')
    keyboard.doModal()
    if not keyboard.isConfirmed() or not (query := keyboard.getText().strip()):
        return
    items = mydramalist.search_dramas(query)
    if not items:
        notify('Nenhum resultado encontrado')
        return
    setcontent('tvshows')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'mdl_id': _mdl_id(url), 'title': title, 'year': year}, destiny='/open_episodes_mdl')
    end()

@route('/filmes_top')
def filmes_top(param=None):
    page = int(param.get('page', 1)) if param else 1
    items = mydramalist.top_movies(page)
    _render_movies(items, page, '/filmes_top')

@route('/filmes_popular')
def filmes_popular(param=None):
    page = int(param.get('page', 1)) if param else 1
    items = mydramalist.popular_movies(page)
    _render_movies(items, page, '/filmes_popular')

@route('/search_filmes')
def search_filmes(param=None):
    keyboard = xbmc.Keyboard('', 'Pesquisar Filme')
    keyboard.doModal()
    if not keyboard.isConfirmed() or not (query := keyboard.getText().strip()):
        return
    items = mydramalist.search_movies(query)
    if not items:
        notify('Nenhum resultado encontrado')
        return
    setcontent('movies')
    for title, img, url, description, score, info, year in items:
        label = f'{title} ({year})' if year else title
        if score: label = f'[COLOR gold]★ {score}[/COLOR]  {label}'
        addMenuItem({'name': label, 'description': f'{info}\n\n{description}'.strip(), 'iconimage': img, 'url': url, 'mdl_id': _mdl_id(url), 'title': title, 'year': year, 'playable': True}, destiny='/play_filme', folder=False)
    end()

@route('/open_episodes_mdl')
def open_episodes_mdl(param):
    serie_title = param.get('title', param.get('name', ''))
    serie_img = param.get('iconimage', '')
    mdl_url = param.get('url', '')
    mdl_id = param.get('mdl_id', '')
    year = param.get('year', '')

    if not mdl_url:
        notify('URL inválida')
        return

    episodes = mydramalist.get_episodes(mdl_url)
    if not episodes:
        notify('Nenhum episódio encontrado')
        return

    setcontent('episodes')
    for ep_num, ep_title, ep_img, ep_desc, air_date, ep_score in episodes:
        label = f'[COLOR gold]★ {ep_score}[/COLOR]  {ep_title}' if ep_score else ep_title
        desc = '\n'.join(filter(None, [air_date, ep_desc]))
        addMenuItem({'name': label, 'description': desc, 'iconimage': ep_img or serie_img, 'serie_title': serie_title, 'episode_num': str(ep_num), 'episode_title': ep_title, 'year': year, 'mdl_id': mdl_id, 'playable': True}, destiny='/play_dorama', folder=False)
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

    notify('PROCURANDO NA FONTE...')

    players = vod_doramas.VOD().tvshow(title=serie_title, mdl_id=mdl_id, season=1, episode=episode_num)
    if not players:
        notify('Nenhum player encontrado')
        return

    if getsetting('autoplay') == 'true':
        order = _autoplay_order(players)
    else:
        player_names = [nome for nome, url in players]
        try:
            escolha = select('ESCOLHA O PLAYER:', player_names)
        except:
            escolha = 0 if player_names else -1
        if escolha < 0:
            return
        order = [escolha] + [i for i in range(len(players)) if i != escolha]

    stream, sub, name = None, None, ''
    for i in order:
        name, player_url = players[i]
        if not player_url:
            continue
        notify(f'Tentando: {name}')
        try:
            stream, sub = resolver.resolverurls(player_url, player_url)
        except:
            stream, sub = None, None
        if stream:
            break

    if not stream:
        notify('STREAM INDISPONÍVEL')
        return

    result = f'{stream}|sub={sub}' if sub else stream

    _play(result, episode_title or serie_title, iconimage, fanart, description, 'episode', '1', str(episode_num), serie_title, serie_title, year)

@route('/play_filme')
def play_filme(param):
    title = param.get('title', param.get('name', ''))
    iconimage = param.get('iconimage', '')
    fanart = param.get('fanart', '')
    description = param.get('description', '')
    year = param.get('year', '')
    mdl_id = param.get('mdl_id', '')

    notify('PROCURANDO NA FONTE...')

    players = vod_doramas.VOD().movie(title=title, mdl_id=mdl_id)
    if not players:
        notify('Nenhum player encontrado')
        return

    if getsetting('autoplay') == 'true':
        order = _autoplay_order(players)
    else:
        player_names = [nome for nome, url in players]
        try:
            escolha = select('ESCOLHA O PLAYER:', player_names)
        except:
            escolha = 0 if player_names else -1
        if escolha < 0:
            return
        order = [escolha] + [i for i in range(len(players)) if i != escolha]

    stream, sub, name = None, None, ''
    for i in order:
        name, player_url = players[i]
        if not player_url:
            continue
        notify(f'Tentando: {name}')
        try:
            stream, sub = resolver.resolverurls(player_url, player_url)
        except:
            stream, sub = None, None
        if stream:
            break

    if not stream:
        notify('STREAM INDISPONÍVEL')
        return

    result = f'{stream}|sub={sub}' if sub else stream

    _play(result, title, iconimage, fanart, description, 'movie', None, None, '', title, year)