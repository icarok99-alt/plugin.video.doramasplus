# -*- coding: utf-8 -*-
import threading
import xbmc
from lib import db
from lib.upnext import get_upnext_service


class DoramaPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._on = False
        self._watched = False
        self._id = None
        self._ep = None
        self._last = 0.0
        self._total = 0.0
        self.upnext = get_upnext_service(self)
        self._monitor_thread = None

    def start_monitoring(self, mdl_id, ep_num, serie_title, next_info=None):
        with self._lock:
            self._on = False

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)

        with self._lock:
            self._id = mdl_id; self._ep = ep_num
            self._on = True; self._watched = False
            self._last = 0.0; self._total = 0.0

        mon = xbmc.Monitor()
        waited = 0
        while waited < 30 and not mon.abortRequested():
            if self.isPlayingVideo() and self.getTotalTime() > 60: break
            mon.waitForAbort(0.5); waited += 0.5
        if not self.isPlayingVideo():
            with self._lock: self._on = False; return
        if next_info:
            self.upnext.start_monitoring(mdl_id, ep_num, serie_title, next_info)
        self._monitor_thread = threading.Thread(target=self._loop, daemon=True)
        self._monitor_thread.start()

    def _loop(self):
        mon = xbmc.Monitor(); total = 0
        for _ in range(60):
            with self._lock:
                if not self._on: return
            try:
                total = self.getTotalTime()
                if total > 60: break
            except Exception: pass
            mon.waitForAbort(0.5)
        if total <= 60:
            with self._lock: self._on = False; return
        with self._lock: self._total = total
        at = total * 0.9
        while self.isPlayingVideo():
            with self._lock:
                if not self._on: break
            if mon.abortRequested(): break
            try: ct = self.getTime()
            except Exception: mon.waitForAbort(0.5); continue
            with self._lock:
                self._last = ct
                if not self._watched and ct >= at:
                    self._watched = True
                    mdl_id, ep = self._id, self._ep
                else:
                    mdl_id, ep = None, None
            if mdl_id and ep is not None:
                threading.Thread(target=db.mark_watched, args=(mdl_id, ep), daemon=True).start()
            mon.waitForAbort(0.5)
        with self._lock: self._on = False

    def _on_stop(self, ended=False):
        with self._lock:
            already = self._watched
            total = self._total
            last = self._last
            mdl_id = self._id
            ep = self._ep
            self._on = False; self._watched = False
            self._id = None; self._ep = None
            self._last = 0.0; self._total = 0.0
        if not already and mdl_id and ep is not None and total > 60:
            if ended or last >= total * 0.9:
                threading.Thread(target=db.mark_watched, args=(mdl_id, ep), daemon=True).start()
        self.upnext.stop_monitoring()

    def onPlayBackStopped(self): self._on_stop()
    def onPlayBackEnded(self): self._on_stop(ended=True)
    def onPlayBackError(self): self._on_stop()

_player = None; _plock = threading.Lock()


def get_player():
    global _player
    with _plock:
        if _player is None: _player = DoramaPlayer()
        return _player