# -*- coding: utf-8 -*-
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

_addon = xbmcaddon.Addon()


class UpNextDialog(xbmcgui.WindowXMLDialog):

    BTN_PLAY   = 3001
    BTN_CANCEL = 3002
    LBL_NEXT   = 3003
    IMG_THUMB  = 3004
    PROGRESS   = 3005

    def __init__(self, *args, **kwargs):
        self.next_info       = kwargs.get('next_info', {})
        self.countdown_secs  = kwargs.get('countdown_secs', 10)
        self.auto_play       = False
        self.cancelled       = False
        self._stop           = False
        self._thread         = None
        self.player          = xbmc.Player()

    def onInit(self):
        try:
            ep_num   = self.next_info.get('ep_num', '')
            ep_title = self.next_info.get('ep_title', '')
            thumb    = self.next_info.get('ep_img', '')

            label = 'Episode {} {}'.format(ep_num, ep_title).strip() if ep_title else 'Episode {}'.format(ep_num)
            self.getControl(self.LBL_NEXT).setLabel(label)
            if thumb:
                self.getControl(self.IMG_THUMB).setImage(thumb)
            try:
                self.setFocusId(self.BTN_PLAY)
            except Exception:
                pass
            self._stop = False
            self._thread = threading.Thread(target=self._countdown, daemon=True)
            self._thread.start()
        except Exception:
            pass

    def _countdown(self):
        remaining = self.countdown_secs
        while remaining > 0 and not self._stop:
            try:
                pct = int((remaining / float(self.countdown_secs)) * 100)
                self.getControl(self.PROGRESS).setPercent(pct)
                self.getControl(self.BTN_PLAY).setLabel('Reproduzir ({})'.format(remaining))
                time.sleep(1)
                remaining -= 1
            except Exception:
                break
        if not self._stop and remaining == 0:
            self.auto_play = True
            self.close()

    def onClick(self, controlId):
        if controlId == self.BTN_PLAY:
            self._seek_to_end()
            self.auto_play = True
            self._stop = True
            self.close()
        elif controlId == self.BTN_CANCEL:
            self.cancelled = True
            self._stop = True
            self.close()

    def onAction(self, action):
        aid = action.getId()
        if aid in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_STOP):
            self.cancelled = True
            self._stop = True
            self.close()
        elif aid in (xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_PLAYER_PLAY):
            try:
                focused = self.getFocusId()
                if focused == self.BTN_PLAY:
                    self._seek_to_end()
                    self.auto_play = True
                    self._stop = True
                    self.close()
                elif focused == self.BTN_CANCEL:
                    self.cancelled = True
                    self._stop = True
                    self.close()
            except Exception:
                pass

    def _seek_to_end(self):
        try:
            total = self.player.getTotalTime()
            if total > 0:
                self.player.seekTime(total - 1)
        except Exception:
            pass

    def doModal(self):
        super().doModal()
        return self.auto_play


class UpNextService:

    def __init__(self, player):
        self.player       = player
        self._lock        = threading.Lock()
        self._stop        = False
        self._monitoring  = False
        self._thread      = None
        self._dialog_shown = False
        self._dialog_lock  = threading.Lock()

    @staticmethod
    def _get_bool(addon, key, default=True):
        try:
            return addon.getSettingBool(key)
        except Exception:
            val = addon.getSetting(key)
            return default if val == '' else val.lower() == 'true'

    @staticmethod
    def _get_int(addon, key, default, minimum):
        try:
            v = addon.getSettingInt(key)
            return max(v if v > 0 else default, minimum)
        except Exception:
            try:
                return max(int(addon.getSetting(key)) or default, minimum)
            except Exception:
                return default

    def _get_settings(self):
        addon = xbmcaddon.Addon()
        enabled   = self._get_bool(addon, 'upnext_enabled')
        countdown = self._get_int(addon, 'upnext_countdown', 10, 5)
        trigger   = self._get_int(addon, 'upnext_trigger', 30, 10)
        return enabled, countdown, trigger

    def start_monitoring(self, mdl_id, ep_num, serie_title, next_info):
        enabled, _, _ = self._get_settings()
        if not enabled:
            return

        with self._dialog_lock:
            self._dialog_shown = False

        with self._lock:
            self._stop = True
            self._monitoring = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        with self._lock:
            self._stop = False
            self._monitoring = True

        self._thread = threading.Thread(
            target=self._loop,
            args=(mdl_id, ep_num, next_info),
            daemon=True
        )
        self._thread.start()

    def _loop(self, mdl_id, ep_num, next_info):
        monitor = xbmc.Monitor()
        enabled, countdown_secs, trigger_secs = self._get_settings()

        waited = 0
        while waited < 30:
            if self.player.isPlayingVideo():
                break
            if monitor.waitForAbort(0.5):
                with self._lock:
                    self._monitoring = False
                return
            waited += 0.5

        if not self.player.isPlayingVideo():
            with self._lock:
                self._monitoring = False
            return

        total_time = 0
        for _ in range(60):
            try:
                total_time = self.player.getTotalTime()
                if total_time > 60:
                    break
            except Exception:
                pass
            if self._stop:
                with self._lock:
                    self._monitoring = False
                return
            monitor.waitForAbort(0.5)

        if total_time <= 60:
            with self._lock:
                self._monitoring = False
            return

        safety = 30
        start_at = min(total_time * 0.9, total_time - trigger_secs - safety)

        while self.player.isPlayingVideo() and not self._stop:
            if monitor.abortRequested():
                break
            try:
                ct = self.player.getTime()
            except Exception:
                monitor.waitForAbort(0.5)
                continue

            if ct < start_at:
                monitor.waitForAbort(0.5)
                continue

            remaining = total_time - ct
            if next_info and remaining <= trigger_secs:
                with self._dialog_lock:
                    if not self._dialog_shown:
                        self._dialog_shown = True
                        self._show_dialog(next_info, countdown_secs)
                        break

            monitor.waitForAbort(0.5)

        with self._lock:
            self._monitoring = False

    def _show_dialog(self, next_info, countdown_secs):
        try:
            addon = xbmcaddon.Addon()
            dialog = UpNextDialog(
                'upnext-dialog.xml',
                addon.getAddonInfo('path'),
                'default', '1080i',
                next_info=next_info,
                countdown_secs=countdown_secs,
            )
            dialog.doModal()
            del dialog
        except Exception:
            pass

    def stop_monitoring(self):
        with self._lock:
            self._stop = True
            self._monitoring = False


_service = None
_service_lock = threading.Lock()


def get_upnext_service(player):
    global _service
    with _service_lock:
        if _service is None:
            _service = UpNextService(player)
        return _service