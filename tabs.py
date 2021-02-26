from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import DynamicContainer, HSplit, FormattedTextControl, Window
from prompt_toolkit.widgets import HorizontalLine

from keys import CustomKeyBindings


class Tab(object):

    def __init__(self, name, body):
        self.name = name
        self.body = body


class Tabs(object):

    def __init__(self, tabs, default_tab, default_body):
        self.tabs = tabs
        self.selected = None
        self.default_tab = default_tab
        self.default_body = default_body
        self.container = DynamicContainer(self.build)

    def current(self):
        self.updateSel()
        return self.selected

    def isEmpty(self):
        return len(self.tabs) == 0

    def add(self, tab):
        self.tabs.append(tab)
        self.selected = tab

    def remove(self, tab):
        self.tabs.remove(tab)
        self.updateSel()
        get_app().layout.focus(self.selected.body)

    def updateSel(self):
        if (self.selected is None or self.selected not in self.tabs) and len(self.tabs) > 0:
            self.selected = self.tabs[0]

    def build(self):
        self.updateSel()

        toolbar = []

        tabs = list(self.tabs)
        if len(tabs) == 0:
            tabs.append(Tab(self.default_tab, self.default_body))

        for tab in tabs:
            color = 'white' if tab == self.selected else '#777777'
            toolbar.append((color, tab.name))
            toolbar.append(('white', ' | '))

        return HSplit([
            Window(
                content=FormattedTextControl(toolbar),
                height=1
            ),
            HorizontalLine(),
            self.selected.body if self.selected else self.default_body
        ])

    def __pt_container__(self):
        return self.container

    def get_keybindings(self):
        kb = CustomKeyBindings()

        this_has_focus = Condition(lambda: not self.isEmpty() and get_app().layout.has_focus(self.current().body))
        this_two_tabs = Condition(
            lambda: not self.isEmpty() and get_app().layout.has_focus(self.current().body) and len(self.tabs) > 1)

        def offset(off):
            index = self.tabs.index(self.selected)
            index += off
            index = index % len(self.tabs)
            self.selected = self.tabs[index]
            get_app().layout.focus(self.selected.body)

        @kb.add('Prev', 'Shift Left', Keys.ShiftLeft, filter=this_two_tabs)
        def left_action(event):
            offset(-1)

        @kb.add('Next', 'Shift Right', Keys.ShiftRight, filter=this_two_tabs)
        def right_action(event):
            offset(1)

        @kb.add('Remove', 'Shift Delete', Keys.ShiftDelete, filter=this_two_tabs)
        def delete(event):
            if len(self.tabs) > 1:
                self.remove(self.selected)

        return kb
