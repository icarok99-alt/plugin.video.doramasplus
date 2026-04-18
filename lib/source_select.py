# -*- coding: utf-8 -*-

import xbmc
import xbmcgui


class SourceSelect(xbmcgui.WindowXMLDialog):

    LIST_ID = 200

    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location)
        try:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            xbmc.executebuiltin('Dialog.Close(busydialog)')
        except Exception:
            pass

        self._players = (actionArgs or {}).get('player_list', [])
        self.selected_index = -1
        self._list = None

        fanart = (actionArgs or {}).get('fanart_path', '')
        if fanart:
            xbmcgui.Window(10000).setProperty('mdl.loading.fanart', fanart)

    def onInit(self):
        try:
            self._list = self.getControl(self.LIST_ID)
            self._list.reset()
            for name, _ in self._players:
                self._list.addItem(xbmcgui.ListItem(name, offscreen=True))
            self.setFocusId(self.LIST_ID)
        except Exception:
            pass

    def onClick(self, controlId):
        if controlId == self.LIST_ID:
            try:
                self.selected_index = self._list.getSelectedPosition()
            except Exception:
                self.selected_index = -1
            self.close()

    def onAction(self, action):
        if action.getId() in [92, 10]:
            self.selected_index = -1
            self.close()

    def doModal(self) -> int:
        super().doModal()
        return self.selected_index

    def close(self):
        self._list = None
        super().close()