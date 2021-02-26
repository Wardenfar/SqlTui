from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import UIControl, UIContent
from prompt_toolkit.utils import Event

from dialogs import loading_dialog, remove_float, inputs_dialog
from keys import CustomKeyBindings

FILE_ITEM_NODE = 'node'
FILE_ITEM_LEAF = 'leaf'


class TreeItem:
    def __init__(self, tree, parent, node_type, formattedText, isOpen, visit_callback, selected_callback):
        self.parent = parent
        self.tree = tree
        self.node_type = node_type
        self.formattedText = formattedText
        self.isOpen = False
        self.children = []
        self.visit_callback = visit_callback
        self.selected_callback = selected_callback
        if isOpen and node_type == FILE_ITEM_NODE:
            self.open()

    def plain_text(self):
        text = ''
        for part in self.formattedText:
            text += part[1]
        return text

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

    def open(self, indexing=False):
        if self.node_type == FILE_ITEM_NODE and self.isOpen:
            return

        if not indexing:
            self.isOpen = True

        if not self.children and self.visit_callback:
            self.children = self.visit_callback(indexing=indexing)

        if not self.parent:
            self.tree.explore_index(self, 0, {"count": 0})

        get_app().invalidate()

    def close(self):
        if self.node_type == FILE_ITEM_NODE and not self.isOpen:
            return
        self.isOpen = False
        # self.children = []
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
        self.depths = {}
        self.search_mode = False
        self.search_results = []
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
        self.depths[len(self.content)] = level
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

        if parent.isOpen:
            for child in parent.children:
                self.explore(child, level + 1)

    def explore_index(self, parent, level, stats):
        if not parent.isOpen:
            parent.open(indexing=True)

        if parent.children:
            stats['count'] += len(parent.children)

            for child in parent.children:
                self.explore_index(child, level + 1, stats)

        # if level == 0:
        #     raise Exception(stats['count'])

    def search_recursive(self, search, parent, results):
        if parent:
            if parent.plain_text().startswith(search):
                results.insert(0, parent)
            elif search in parent.plain_text():
                results.append(parent)

            if parent.children:
                for child in parent.children:
                    self.search_recursive(search, child, results)
        return results

    def get_root_selected(self):
        curr = self.cursorItem
        while curr.parent:
            curr = curr.parent
        return curr

    def reveal_item(self, item):
        curr = item
        while curr.parent:
            curr.open()
            curr = curr.parent
        self.cursorItem = item
        self.refresh()
        get_app().invalidate()

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

        in_search_mode = Condition(lambda: self.search_mode)
        current_is_root = Condition(lambda: self.cursorItem in self.roots)

        @kb.add('Down', 'Down', Keys.Down, filter=~in_search_mode)
        def _(event):
            offsetCursor(1)

        @kb.add('Up', 'Up', Keys.Up, filter=~in_search_mode)
        def _(event):
            offsetCursor(-1)

        @kb.add('Goto Parent', 'Shift-Up', Keys.ShiftUp, filter=~in_search_mode)
        def _(event):
            depth = self.depths[self.cursorIndex]
            if self.cursorIndex > 0 and self.depths[self.cursorIndex - 1] < depth:
                offsetCursor(-1)
            else:
                for i in range(self.cursorIndex - 1, -1, -1):
                    if self.depths[i] < depth:
                        offsetCursor(i - self.cursorIndex)
                        break

        @kb.add('Goto Next', 'Shift-Down', Keys.ShiftDown, filter=~in_search_mode)
        def _(event):
            depth = self.depths[self.cursorIndex]
            found = False
            for i in range(self.cursorIndex + 1, len(self.content), 1):
                if self.depths[i] == depth:
                    offsetCursor(i - self.cursorIndex)
                    found = True
                    break
            if not found:
                for i in range(self.cursorIndex + 1, len(self.content), 1):
                    if self.depths[i] > depth:
                        offsetCursor(i - self.cursorIndex)
                        found = True
                        break

        @kb.add(None, None, "space")
        @kb.add('Toggle', 'Enter', "enter", filter=~in_search_mode)
        def _(event):
            if self.cursorItem is not None:
                self.cursorItem.toggle()
            elif len(self.roots) > 0:
                self.cursorItem = self.roots[0]
                self.cursorItem.toggle()

        @kb.add('Index All Tree', 'F6', Keys.F6, filter=~in_search_mode & current_is_root)
        def _(event):
            float_dialog = loading_dialog(title='Indexing')
            self.explore_index(self.cursorItem, 0, {"count": 0})
            remove_float(float_dialog)

        @kb.add('Search', '/', '/', filter=~in_search_mode)
        def _(event):
            def callback(result):
                search_results = self.search_recursive(result['Search'], self.get_root_selected(), [])
                if len(search_results) == 0:
                    return

                self.search_mode = True
                self.search_results = search_results
                self.reveal_item(search_results[0])
                get_app().invalidate()

            inputs_dialog(callback, title="Enter a search", inputs_data=['Search'])

        @kb.add('Next', 'Down', Keys.Down, filter=in_search_mode)
        def _(event):
            index = self.search_results.index(self.cursorItem)
            index = (index + 1) % len(self.search_results)
            self.reveal_item(self.search_results[index])

        @kb.add('Prev', 'Up', Keys.Up, filter=in_search_mode)
        def _(event):
            index = self.search_results.index(self.cursorItem)
            index = (index - 1) % len(self.search_results)
            self.reveal_item(self.search_results[index])

        @kb.add('Exit Search Mode', 'Esc', Keys.Escape, filter=in_search_mode)
        def _(event):
            self.search_mode = False
            self.search_results = []
            get_app().invalidate()

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
            if self.search_mode and index == height - 1:
                return [('reverse', ' Search' + (' ' * (width - 7)))]

            with_offset = index - offset
            if with_offset < 0 or with_offset >= len(self.indexes.keys()):
                return [('', '')]

            line = self.content[with_offset]
            if with_offset == cursor:
                line = line.copy()
                for i in range(1, len(line)):
                    line[i] = ('reverse ' + line[i][0], line[i][1])

            return line

        return UIContent(
            get_line=get_line,
            line_count=height)
