import threading
import xbmc
from lib import db
from lib.upnext import get_upnext_service

RESUME_MIN_FRACTION = 0.02
RESUME_MAX_FRACTION = 0.85
WATCHED_FRACTION = 0.90
MIN_DURATION = 60


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

    def start_monitoring(self, mdl_id, ep_num, serie_title, next_info=None, resume_time=None):
        with self._lock:
            self._on = False

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)

        with self._lock:
            self._id = mdl_id
            self._ep = ep_num
            self._on = True
            self._watched = False
            self._last = 0.0
            self._total = 0.0

        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(mdl_id, ep_num, serie_title),
            kwargs={'next_info': next_info, 'resume_time': resume_time},
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitoring_loop(self, mdl_id, ep_num, serie_title, next_info=None, resume_time=None):
        monitor = xbmc.Monitor()

        waited = 0
        while waited < 30 and not monitor.abortRequested():
            if self.isPlayingVideo():
                break
            monitor.waitForAbort(0.5)
            waited += 0.5

        if not self.isPlayingVideo():
            with self._lock:
                self._on = False
            return

        total = 0.0
        for _ in range(60):
            with self._lock:
                if not self._on:
                    return
            try:
                total = self.getTotalTime()
                if total > MIN_DURATION:
                    break
            except Exception:
                pass
            monitor.waitForAbort(0.5)

        if total <= MIN_DURATION:
            with self._lock:
                self._on = False
            return

        with self._lock:
            self._total = total

        if resume_time and 0 < resume_time < total * RESUME_MAX_FRACTION:
            try:
                self.seekTime(float(resume_time))
            except Exception:
                pass

        if next_info:
            self.upnext.start_monitoring(mdl_id, ep_num, serie_title, next_info)

        watched_at = total * WATCHED_FRACTION

        while self.isPlayingVideo():
            with self._lock:
                if not self._on:
                    break
            if monitor.abortRequested():
                break

            try:
                ct = self.getTime()
            except Exception:
                monitor.waitForAbort(0.5)
                continue

            with self._lock:
                self._last = ct
                if not self._watched and ct >= watched_at:
                    self._watched = True
                    do_mark = True
                else:
                    do_mark = False

            if do_mark:
                threading.Thread(target=db.mark_watched, args=(mdl_id, ep_num), daemon=True).start()
                threading.Thread(target=db.clear_resume_time, args=(mdl_id, ep_num), daemon=True).start()

            monitor.waitForAbort(0.5)

        with self._lock:
            watched = self._watched
            last = self._last
            self._on = False

        if not watched and total > MIN_DURATION and last > 0:
            fraction = last / total
            if RESUME_MIN_FRACTION < fraction < RESUME_MAX_FRACTION:
                db.save_resume_time(mdl_id, ep_num, last, total)
            elif fraction >= RESUME_MAX_FRACTION:
                db.clear_resume_time(mdl_id, ep_num)

    def _on_stop(self, ended=False):
        with self._lock:
            already = self._watched
            total = self._total
            last = self._last
            mdl_id = self._id
            ep = self._ep
            self._on = False
            self._watched = False
            self._id = None
            self._ep = None
            self._last = 0.0
            self._total = 0.0

        self.upnext.stop_monitoring()

        if not mdl_id or ep is None or total <= MIN_DURATION:
            return

        if not already and (ended or last >= total * WATCHED_FRACTION):
            threading.Thread(target=db.mark_watched, args=(mdl_id, ep), daemon=True).start()
            threading.Thread(target=db.clear_resume_time, args=(mdl_id, ep), daemon=True).start()
        elif not already and last > 0:
            fraction = last / total
            if RESUME_MIN_FRACTION < fraction < RESUME_MAX_FRACTION:
                db.save_resume_time(mdl_id, ep, last, total)
            elif fraction >= RESUME_MAX_FRACTION:
                db.clear_resume_time(mdl_id, ep)

    def onPlayBackStopped(self): self._on_stop()
    def onPlayBackEnded(self): self._on_stop(ended=True)
    def onPlayBackError(self): self._on_stop()


_player = None
_plock = threading.Lock()


def get_player():
    global _player
    with _plock:
        if _player is None:
            _player = DoramaPlayer()
        return _player
