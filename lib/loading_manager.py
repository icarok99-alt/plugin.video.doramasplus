# -*- coding: utf-8 -*-
import os
import threading
import xbmc
import xbmcaddon
import xbmcgui

from lib.loading_window import LoadingWindow
from lib.source_select import SourceSelect


class _Monitor(xbmc.Player):

    def __init__(self):
        super().__init__()
        self._av_ready = threading.Event()
        self._failed = threading.Event()
        self._armed = False
        self._lock = threading.Lock()

    def onAVStarted(self):
        with self._lock:
            if self._armed:
                self._av_ready.set()

    def onPlayBackError(self):
        with self._lock:
            if self._armed:
                self._failed.set()

    def onPlayBackStopped(self):
        with self._lock:
            if self._armed:
                self._failed.set()

    def reset(self):
        with self._lock:
            self._av_ready.clear()
            self._failed.clear()
            self._armed = True

    def disarm(self):
        with self._lock:
            self._armed = False
            self._failed.set()

    def wait(self, timeout: float = 45.0) -> bool:
        mon = xbmc.Monitor()
        deadline = time.monotonic() + timeout

        phase1_ok = False
        while time.monotonic() < deadline:
            if self._failed.is_set() or mon.abortRequested():
                return False
            if self._av_ready.is_set():
                phase1_ok = True
                break
            try:
                if self.isPlaying() and self.getTime() > 0.0:
                    phase1_ok = True
                    break
            except Exception:
                pass
            mon.waitForAbort(0.1)

        if not phase1_ok:
            return False

        last_pos = -1.0
        confirm_deadline = min(time.monotonic() + 0.4, deadline)

        while time.monotonic() < confirm_deadline:
            if self._failed.is_set() or mon.abortRequested():
                return False
            try:
                if not self.isPlaying():
                    return False
                pos = self.getTime()
            except Exception:
                mon.waitForAbort(0.1)
                continue
            if last_pos >= 0.0 and pos > last_pos:
                return True
            last_pos = pos
            mon.waitForAbort(0.1)

        try:
            return self._av_ready.is_set() and self.isPlaying() and self.getTime() >= 0.0
        except Exception:
            return self._av_ready.is_set()


class LoadingManager:

    _ANIM_STEP_MS = 60
    _ANIM_PAUSE_MS = 200
    _PLAYER_TIMEOUT = 45.0

    def __init__(self):
        self.window = None
        self._lock = threading.Lock()
        self._anim_t = None
        self._anim_on = False
        self._sup_t = None
        self._sup_on = False
        self._mon_t = None
        self._closing = False
        self._player_mon = _Monitor()

        addon = xbmcaddon.Addon()
        self._path = addon.getAddonInfo('path')
        self._fanart = os.path.join(self._path, 'fanart.jpg')

    def _anim_loop(self):
        try:
            while self._anim_on:
                for i in range(0, 101, 2):
                    if not self._anim_on:
                        return
                    try:
                        xbmcgui.Window(10000).setProperty('mdl.loading.progress', str(i))
                    except Exception:
                        pass
                    xbmc.sleep(self._ANIM_STEP_MS)
                if self._anim_on:
                    xbmc.sleep(self._ANIM_PAUSE_MS)
        except Exception:
            pass

    def _start_anim(self):
        self._anim_on = True
        if self._anim_t is None or not self._anim_t.is_alive():
            self._anim_t = threading.Thread(target=self._anim_loop, daemon=True, name='mdl-anim')
            self._anim_t.start()

    def _ensure_anim(self):
        if self._anim_on and (self._anim_t is None or not self._anim_t.is_alive()):
            self._anim_t = threading.Thread(target=self._anim_loop, daemon=True, name='mdl-anim-wd')
            self._anim_t.start()

    def _stop_anim(self):
        self._anim_on = False
        try:
            xbmcgui.Window(10000).clearProperty('mdl.loading.progress')
        except Exception:
            pass

    def _sup_loop(self):
        try:
            while self._sup_on:
                xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
                xbmc.executebuiltin('Dialog.Close(busydialog)')
                xbmc.sleep(100)
        except Exception:
            pass

    def _start_sup(self):
        self._sup_on = True
        if self._sup_t is None or not self._sup_t.is_alive():
            self._sup_t = threading.Thread(target=self._sup_loop, daemon=True, name='mdl-sup')
            self._sup_t.start()

    def show(self):
        with self._lock:
            try:
                self._closing = False
                self._player_mon.reset()
                xbmcgui.Window(10000).setProperty('mdl.loading.phase', '1')
                if self.window is None:
                    self.window = LoadingWindow(
                        'DialogLoading.xml', self._path,
                        actionArgs={'fanart_path': self._fanart})
                    self.window.show()
                self._start_anim()
                self._start_sup()
            except Exception:
                pass

    def set_phase2(self, player_list: list) -> int:
        try:
            fanart = xbmcgui.Window(10000).getProperty('mdl.loading.fanart')
            sel = SourceSelect(
                'DialogSourceSelect.xml', self._path,
                actionArgs={'fanart_path': fanart, 'player_list': player_list})
            idx = sel.doModal()
            xbmcgui.Window(10000).setProperty('mdl.loading.phase', '3')
            return idx
        except Exception:
            return -1

    def set_resolving(self):
        with self._lock:
            try:
                xbmcgui.Window(10000).setProperty('mdl.loading.phase', '3')
                self._closing = True
                self._player_mon.reset()
                self._start_sup()
                self._start_anim()
                if self._mon_t is None or not self._mon_t.is_alive():
                    self._mon_t = threading.Thread(target=self._wait_close, daemon=True, name='mdl-mon')
                    self._mon_t.start()
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._closing = True
            if self._mon_t is None or not self._mon_t.is_alive():
                self._mon_t = threading.Thread(target=self._wait_close, daemon=True, name='mdl-mon')
                self._mon_t.start()

    def force_close(self):
        with self._lock:
            self._sup_on = False
            self._closing = False
            self._player_mon.disarm()
            self._stop_anim()
            if self.window:
                try:
                    self.window.close()
                except Exception:
                    pass
                self.window = None
            self._clear_props()

    def _wait_close(self):
        self._ensure_anim()
        self._player_mon.wait(timeout=self._PLAYER_TIMEOUT)
        self._do_close()

    def _do_close(self):
        with self._lock:
            if self.window and self._closing:
                try:
                    self._sup_on = False
                    self._stop_anim()
                    self.window.close()
                    self.window = None
                except Exception:
                    pass

    @staticmethod
    def _clear_props():
        win = xbmcgui.Window(10000)
        for prop in ('mdl.loading.fanart', 'mdl.loading.phase', 'mdl.loading.progress'):
            try:
                win.clearProperty(prop)
            except Exception:
                pass


loading_manager = LoadingManager()
