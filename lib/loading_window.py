# -*- coding: utf-8 -*-

import xbmc
import xbmcgui


class LoadingWindow(xbmcgui.WindowXMLDialog):

    _PROPS = (
        'mdl.loading.progress',
        'mdl.loading.phase',
        'mdl.loading.fanart',
    )

    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location)
        try:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            xbmc.executebuiltin('Dialog.Close(busydialog)')
        except Exception:
            pass

        fanart = (actionArgs or {}).get('fanart_path', '')
        if fanart:
            xbmcgui.Window(10000).setProperty('mdl.loading.fanart', fanart)

        self.canceled = False

    def onAction(self, action):
        if action.getId() in [92, 10]:
            self.canceled = True
            self.close()

    def close(self):
        win = xbmcgui.Window(10000)
        for prop in self._PROPS:
            try:
                win.clearProperty(prop)
            except Exception:
                pass
        super().close()