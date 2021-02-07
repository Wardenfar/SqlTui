from prompt_toolkit.application import get_app
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import UIControl, UIContent
from prompt_toolkit.utils import Event

from keys import CustomKeyBindings

FILE_ITEM_NODE = 'node'
FILE_ITEM_LEAF = 'leaf'


class TreeItem:
    def __init__(self, tree, node_type, formattedText, isOpen, visit_callback, selected_callback):
        self.tree = tree
        self.node_type = node_type
        self.formattedText = formattedText
        self.isOpen = False
        self.children = []
        self.visit_callback = visit_callback
        self.selected_callback = selected_callback
        if isOpen and node_type == FILE_ITEM_NODE:
            self.open()

    def hash(self):
        return self.formattedText

    def size(self):
        return 1 + sum(map(lambda f: f.size, self.children))

    def toggle(self):
        if self.node_type == FILE_ITEM_NODE:
            if self.isOpen:
                self.close()
            else:
                self.open()
        else:
            if self.visit_callback:
                self.visit_callback()
        self.tree.dirty = True
        get_app().invalidate()

    def refresh(self):
        if self.isOpen and self.visit_callback:
            self.tree.dirty = True
            oldChildren = self.children
            newChildren = self.visit_callback()

            oldHash = [child.hash() for child in oldChildren]
            newHash = [child.hash() for child in newChildren]

            unchanged = []

            for old in oldChildren:
                if old.hash() in newHash:
                    old.refresh()
                else:
                    self.children.remove(old)

            for new in newChildren:
                if new.hash() not in oldHash and new.hash() not in unchanged:
                    self.children.insert(newChildren.index(new), new)

    def open(self):
        if self.node_type == FILE_ITEM_NODE and self.isOpen:
            return

        self.isOpen = True
        if self.visit_callback:
            self.children = self.visit_callback()
        get_app().invalidate()

    def close(self):
        if self.node_type == FILE_ITEM_NODE and not self.isOpen:
            return
        self.isOpen = False
        self.children = []
        get_app().invalidate()


class Tree(UIControl):

    def __init__(self, selected_callback):
        self.selected_callback = selected_callback
        self.invalidateEvent = Event(self)
        self.roots = []
        self.cursorItem = None
        self.cursorIndex = 0
        self.dirty = True
        self.content = []
        self.indexes = {}
        self.refresh()

    def refresh(self):
        self.dirty = False
        self.content = []
        self.indexes = {}
        oldIndex = self.cursorIndex
        self.cursorIndex = -1
        for root in self.roots:
            self.explore(root, 0)
        if self.cursorIndex == -1:
            if oldIndex >= len(self.content):
                self.cursorIndex = 0
                if len(self.roots) > 0:
                    self.cursorItem = self.roots[0]
            else:
                self.cursorIndex = oldIndex
                self.cursorItem = self.indexes[oldIndex]

    def explore(self, parent, level):
        self.indexes[len(self.content)] = parent
        if self.cursorItem == parent and self.cursorIndex != len(self.content):
            self.cursorIndex = len(self.content)
            if self.selected_callback:
                self.selected_callback(self.cursorItem)
            if self.cursorItem.selected_callback:
                self.cursorItem.selected_callback()

        line = [
            ('', '  ' * level)
        ]

        for part in parent.formattedText:
            line.append(part)

        self.content.append(line)

        for child in parent.children:
            self.explore(child, level + 1)

    def get_key_bindings(self):
        kb = CustomKeyBindings()

        def offsetCursor(offset):
            self.cursorIndex = self.cursorIndex + offset
            if self.cursorIndex < 0:
                self.cursorIndex = 0
            if self.cursorIndex >= len(self.indexes.keys()):
                self.cursorIndex = len(self.indexes.keys()) - 1

            self.cursorItem = self.indexes[self.cursorIndex]

            if self.selected_callback:
                self.selected_callback(self.cursorItem)
            if self.cursorItem.selected_callback:
                self.cursorItem.selected_callback()

            self.invalidateEvent.fire()

        @kb.add('Down', 'Down', Keys.Down)
        def _(event):
            offsetCursor(1)

        @kb.add('Up', 'Up', Keys.Up)
        def _(event):
            offsetCursor(-1)

        @kb.add(None, None, "space")
        @kb.add('Toggle', 'Enter', "enter")
        def _(event):
            if self.cursorItem is not None:
                self.cursorItem.toggle()
            elif len(self.roots) > 0:
                self.cursorItem = self.roots[0]
                self.cursorItem.toggle()

        return kb

    def get_invalidate_events(self):
        return [self.invalidateEvent]

    def is_focusable(self):
        return True

    def mouse_handler(self, mouse_event):
        return True

    def create_content(self, width, height):
        if self.dirty:
            self.refresh()

        cursor = self.cursorIndex

        offset = 0
        if cursor > height // 2:
            offset = height // 2 - cursor

        def get_line(index):
            withOffset = index - offset
            if withOffset < 0 or withOffset >= len(self.indexes.keys()):
                return [('', '')]

            line = self.content[withOffset]
            if withOffset == cursor:
                line = line.copy()
                for i in range(1, len(line)):
                    line[i] = ('reverse ' + line[i][0], line[i][1])

            return line

        return UIContent(
            get_line=get_line,
            line_count=len(self.content))
