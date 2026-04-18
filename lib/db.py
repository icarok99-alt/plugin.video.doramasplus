# -*- coding: utf-8 -*-
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

try:
    import xbmcvfs
    import xbmcaddon
    _profile = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
except Exception:
    _profile = os.path.expanduser('~/.doramasplus')

_db_path = os.path.join(_profile, 'doramasplus.db')


def _init_db():
    if not os.path.exists(_profile):
        os.makedirs(_profile)
    con = sqlite3.connect(_db_path)
    cur = con.cursor()
    try:
        cur.execute('''CREATE TABLE IF NOT EXISTS episodes (
            mdl_id TEXT NOT NULL, ep_num INTEGER NOT NULL,
            ep_title TEXT, ep_img TEXT, ep_desc TEXT,
            air_date TEXT, ep_score TEXT, updated_at TEXT,
            PRIMARY KEY (mdl_id, ep_num))''')
        cur.execute('''CREATE TABLE IF NOT EXISTS watched (
            mdl_id TEXT NOT NULL, ep_num INTEGER NOT NULL,
            watched_at TEXT, PRIMARY KEY (mdl_id, ep_num))''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_eps ON episodes(mdl_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_w   ON watched(mdl_id)')
        con.commit()
    finally:
        con.close()

_init_db()


@contextmanager
def _conn():
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def save_episodes(mdl_id, episodes):
    if not episodes:
        return
    now  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = [(mdl_id, n, t, i, d, a, s, now) for n, t, i, d, a, s in episodes]
    with _conn() as con:
        con.executemany('''INSERT INTO episodes
            (mdl_id,ep_num,ep_title,ep_img,ep_desc,air_date,ep_score,updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(mdl_id,ep_num) DO UPDATE SET
            ep_title=excluded.ep_title, ep_img=excluded.ep_img,
            ep_desc=excluded.ep_desc, air_date=excluded.air_date,
            ep_score=excluded.ep_score, updated_at=excluded.updated_at''', rows)


def get_episodes(mdl_id):
    with _conn() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM episodes WHERE mdl_id=? ORDER BY ep_num', (mdl_id,))
        return [dict(r) for r in cur.fetchall()]


def get_next_episode(mdl_id, ep_num):
    with _conn() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM episodes WHERE mdl_id=? AND ep_num=?', (mdl_id, ep_num + 1))
        row = cur.fetchone()
        return dict(row) if row else None


def mark_watched(mdl_id, ep_num):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with _conn() as con:
        con.cursor().execute(
            'INSERT OR REPLACE INTO watched(mdl_id,ep_num,watched_at) VALUES(?,?,?)',
            (mdl_id, int(ep_num), now))


def get_watched(mdl_id):
    with _conn() as con:
        cur = con.cursor()
        cur.execute('SELECT ep_num FROM watched WHERE mdl_id=?', (mdl_id,))
        return {row[0] for row in cur.fetchall()}


def is_watched(mdl_id, ep_num):
    with _conn() as con:
        cur = con.cursor()
        cur.execute('SELECT 1 FROM watched WHERE mdl_id=? AND ep_num=?', (mdl_id, int(ep_num)))
        return cur.fetchone() is not None