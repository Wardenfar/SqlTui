import re

import toml
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.keys import Keys

from dialogs import buttons_dialog
from driver import DRIVERS
from keys import CustomKeyBindings
from tree import FILE_ITEM_LEAF
from tree import Tree, FILE_ITEM_NODE
from tree import TreeItem

servers = toml.load('config/servers.toml')['servers']


class Root:
    def __init__(self, dsn, driver):
        self.dsn = dsn
        self.driver = driver

    def __str__(self):
        return self.driver.name + ' <' + self.dsn['host'] + ':' + self.dsn['port'] + '>'


def replace_query(conn, query, parents):
    matched_strings = [m.group(1) for m in re.finditer('#{([^}]*?)}', query)]
    names = []
    types = []
    for m in matched_strings:
        type = None
        name = m
        if ':' in m:
            name = m.split(':')[0]
            type = m.split(':')[1]
        names.append(name)
        types.append(type)

    new_query = query
    for i, m in enumerate(matched_strings):
        type = types[i]
        value = parents[names[i]].data[0]
        new_query = new_query.replace('#{' + m + '}', conn.escape(type, value))

    return new_query


class DbTreeItem(TreeItem):

    def getRoot(self):
        return self.parents['__root__']

    def create_execute_callback(self, tab_name, conn_type, query):
        def callback():
            self.execute(tab_name, conn_type, query)

        return callback

    def execute(self, tab_name, conn_type, query):
        def after():
            self.parents[conn_type].refresh()

        conn = self.connections[conn_type]
        replacedQuery = replace_query(conn, query, self.parents)
        self.tree.execute(tab_name, conn, replacedQuery, after)

    def create_button(self, button):
        def visit_callback():
            self.execute(button[1], button[2], button[3])

        return TreeItem(self.tree, FILE_ITEM_LEAF, [(button[1], button[0])], False, visit_callback, None)

    def get_connection(self, type):
        if type not in self.connections:
            conn = self.getRoot().driver.open_connection(type, self.parents)
            self.connections[type] = conn
        else:
            conn = self.connections[type]
        return conn

    def visit_callback(self):
        children = []
        if 'children_array' in self.node_data:
            array = self.node_data['children_array']
            for row in array:
                children.append(
                    DbTreeItem(self.tree, row[0], self.connections.copy(), (row[1],),
                               self.parents.copy()))
        else:
            query_data = self.node_data['children_query']
            conn = self.get_connection(query_data[0])
            query = replace_query(conn, query_data[1], self.parents)
            result = [row for row in conn.execute(query)[0]]

            for r in result:
                children.append(
                    DbTreeItem(self.tree, self.node_data['children_type'], self.connections.copy(), r,
                               self.parents.copy()))

        if 'extra_children' in self.node_data:
            for button in self.node_data['extra_children']:
                children.append(self.create_button(button))
        return children

    def __init__(self, tree, key, connections, data, parents):
        self.key = key
        self.connections = connections
        self.data = data
        self.parents = parents

        self.node_data = self.getRoot().driver.nodes[self.key]
        self.open_action = self.node_data['open'] if 'open' in self.node_data else None
        self.actions = self.node_data['actions'] if 'actions' in self.node_data else []
        self.parents[self.key] = self

        has_children = 'children_query' in self.node_data or 'children_array' in self.node_data

        callback = self.visit_callback if has_children else None

        if isinstance(data, tuple):
            self.name = data[0] if len(data) <= 1 else data[1]
        else:
            self.name = str(data)

        isOpen = False
        if 'open' in self.node_data and self.node_data['open'] is True:
            isOpen = True

        super().__init__(tree, FILE_ITEM_NODE, [(self.node_data['color'], self.name)], isOpen, callback, None)


class DatabaseTree:

    def __init__(self, execute, add_tab):
        self.execute = execute

        self.tree = Tree(self.itemSelected)
        self.tree.execute = execute
        self.tree.add_tab = add_tab
        self.tree.roots = []
        for server_key in servers:
            self.addServer(servers[server_key])
        # self.tree.refresh()

    def is_selected_cls(self, cls):
        if self.tree.cursorItem:
            return isinstance(self.tree.cursorItem, cls)
        return False

    def get_keybindings(self):
        kb = CustomKeyBindings()

        this_has_focus = Condition(lambda: get_app().layout.has_focus(self.tree))
        has_actions = Condition(lambda: get_app().layout.has_focus(self.tree)
                                        and hasattr(self.tree.cursorItem, 'actions')
                                        and len(self.tree.cursorItem.actions) > 0)

        can_open = Condition(
            lambda: get_app().layout.has_focus(self.tree)
                    and hasattr(self.tree.cursorItem, 'open_action')
                    and self.tree.cursorItem.open_action)

        @kb.add('Refresh', 'F5', Keys.F5, filter=this_has_focus)
        def refresh_action(event):
            selItem = self.tree.cursorItem
            if selItem:
                selItem.refresh()

        @kb.add('Actions', 'a', 'a', filter=has_actions)
        def open_actions(event):
            selItem = self.tree.cursorItem

            actions = []
            for a in selItem.actions:
                actions.append([a[0], selItem.create_execute_callback(a[0], a[1], a[2])])

            buttons_dialog(
                'Actions for ' + selItem.name,
                actions
            )

        @kb.add('Open Connection', 'o', 'o', filter=can_open)
        def set_conn_serv(event):
            selItem = self.tree.cursorItem
            open_action = selItem.open_action
            conn = selItem.get_connection(open_action[0])
            text = replace_query(conn, open_action[1], selItem.parents)
            self.tree.add_tab('New tab', conn, text)

        return kb

    def itemSelected(self, item):
        pass

    def addServer(self, dsn):
        #
        # driver_name = text.split('://')[0]
        # second_part = text.split('://')[1]
        #
        # creds = second_part.split('@')[0]
        # user = creds.split(':')[0]
        # password = creds.split(':')[1]
        #
        # addr = second_part.split('@')[1]
        # host = addr.split(':')[0]
        # port = addr.split(':')[1]
        #
        # dsn = {
        #     'driver': driver_name,
        #     'user': user,
        #     'password': password,
        #     'host': host,
        #     'port': port
        # }

        driver = DRIVERS[dsn['driver']]

        root = Root(dsn, driver)

        serverItem = DbTreeItem(self.tree, driver.root, {}, root, {'__root__': root})
        self.tree.roots.insert(0, serverItem)
        self.tree.cursorItem = serverItem

        if self.tree.selected_callback:
            self.tree.selected_callback(serverItem)
        if self.tree.cursorItem.selected_callback:
            self.tree.cursorItem.selected_callback()

        self.tree.refresh()
        # get_app().layout.focus(self.tree)
        get_app().invalidate()
