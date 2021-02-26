import re

from math import floor
from prompt_toolkit import Application, HTML
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import has_focus, is_true
from prompt_toolkit.key_binding import merge_key_bindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Window, HSplit, BufferControl, Layout, VSplit, FloatContainer, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.widgets import HorizontalLine, Label
from time import time

from db_tree import DatabaseTree
from dialogs import inputs_dialog
from frame import CustomFrame
from keys import CustomKeyBindings
from table import DynamicTable
from tabs import Tabs, Tab

current_connection = None


def execute_params(tab_name, conn, query, after=None):
    matched_strings = [m.group(1) for m in re.finditer('\\${([^}]*?)}', query)]
    matches = []
    for s in matched_strings:
        if s not in matches:
            matches.append(s)

    if len(matches) > 0:

        names = []
        types = []
        for m in matches:
            type = None
            name = m
            if ':' in m:
                name = m.split(':')[0]
                type = m.split(':')[1]
            names.append(name)
            types.append(type)

        def callback(result):
            new_query = query
            for i, m in enumerate(matches):
                type = types[i]
                value = result[names[i]]
                new_query = new_query.replace('${' + m + '}', conn.escape(type, value))
            execute(tab_name, conn, new_query, after)

        inputs_dialog(callback, 'Enter params', query, names)
    else:
        execute(tab_name, conn, query, after)


def set_tab_text(tab, text):
    tab.body.children[2].content.buffer.text = text


def get_tab_text(tab):
    return tab.body.children[2].content.buffer.text


def add_tab(tab_name, conn, content):
    tab = Tab(tab_name, HSplit([
        Window(height=1, content=FormattedTextControl([('green', str(conn))])),
        HorizontalLine(),
        Window(content=BufferControl(
            lexer=PygmentsLexer(conn.lexer())
        ))
    ]))
    tab.conn = conn
    set_tab_text(tab, content)
    windows['query'].add(tab)


last_time = -1
last_viewport = None


def calculateResultDataViewport():
    global last_time, last_viewport
    now = time()
    if last_viewport is None or (now - last_time) > 5:
        size = get_app().output.get_size()
        width = size.columns / 2 - 5
        height = size.rows - 10
        viewport = (floor(width / 15), floor(height / 3))
        last_time = now
        last_viewport = viewport
        return viewport
    else:
        return last_viewport


def execute(tab_name, conn, query, callback=None):
    if windows['query'].isEmpty() or get_tab_text(windows['query'].current()) != query:
        add_tab(tab_name, conn, query)
    try:
        result, columns = conn.execute(query)

        if len(result) > 0:
            if len(columns) > 0:
                columnLabels = [Label(col) for col in columns]
                rowsLabels = [[Label(str(cell)) for cell in row] for row in result]

                # console = Console(file=StringIO())
                # console.print(table)
                # str_output = console.file.getvalue()

                windows['result_text'].buffer.text = str(len(result)) + ' Rows'
                windows['result_data'].reset(data=rowsLabels, header=columnLabels,
                                             viewport=calculateResultDataViewport(),
                                             max=(len(columns), len(result)))
            else:
                windows['result_text'].buffer.text = 'Affected rows ' + str(len(result))
        else:
            windows['result_text'].buffer.text = 'Executed ! (no rows)'
        windows['tree'].dirty = True
    except Exception as e:
        windows['result_text'].buffer.text = str(e)

    if callback:
        callback()

    get_app().invalidate()


def frame_title(name, key):
    return HTML(name + ' <b><reverse>[' + key + ']</reverse></b>').formatted_text


tree = DatabaseTree(execute_params, add_tab)

queryTabs = Tabs(
    [],
    default_tab='<No Connection>',
    default_body=Window(content=FormattedTextControl([('red', 'Connect first')]))
)

windows = {
    'tree': tree.tree,
    'query': queryTabs,
    'result_text': BufferControl(buffer=Buffer()),
    'result_data': DynamicTable(),
    'bindings_toolbar': FormattedTextControl([('#ffffff', '[F1] [F2] [F3]')])
}

root_container = FloatContainer(
    content=HSplit([
        VSplit([
            CustomFrame(
                title=frame_title('TreeView', 'F1'),
                body=Window(
                    content=windows['tree']
                ),
                width=D(weight=1),
                style="class:focus.tree"
            ),
            HSplit([
                CustomFrame(
                    title=frame_title('Query', 'F2'),
                    body=windows['query'],
                    width=D(weight=1),
                    style="class:focus.query"
                ),
                CustomFrame(
                    title=frame_title('Result Panel', 'F3'),
                    body=HSplit([
                        Window(
                            content=windows['result_text'],
                            height=2
                        ),
                        windows['result_data'].container
                    ]),
                    style="class:focus.result"
                ),
            ], width=D(weight=2))
        ]),
        Window(
            content=windows['bindings_toolbar'],
            height=2,
            wrap_lines=True
        )
    ]),
    floats=[]
)

layout = Layout(root_container)

kb = CustomKeyBindings()


# @kb.add(Keys.F1)
# def exit_(event):
#     get_app().layout.focus(fileTree)
#
# @kb.add(Keys.F2)
# def exit_(event):
#     get_app().layout.focus(term1.container)

@kb.add('Switch Window', 'Tab', 'tab')
def focusTree(event):
    get_app().layout.focus_next()


@kb.add(None, None, Keys.F1)
def focusTree(event):
    get_app().layout.focus(windows['tree'])


@kb.add(None, None, Keys.F2)
def focusQuery(event):
    if not windows['query'].isEmpty():
        get_app().layout.focus(windows['query'].current().body)


@kb.add(None, None, Keys.F3)
def focusResult(event):
    get_app().layout.focus(windows['result_data'].container)


@kb.add(None, None, Keys.ControlC)
def exit_(event):
    get_app().exit()


@kb.add('Execute', 'Ctrl-E', Keys.ControlE, filter=has_focus(windows['query'].container))
def _execute(event):
    if not windows['query'].isEmpty():
        tab = windows['query'].current()
        text = get_tab_text(tab)
        execute(tab.name, tab.conn, text)


def before_render(event):
    kb = get_app().key_bindings

    text = []

    def add_binding(b):
        if is_true(b.filter) and hasattr(b, 'name') and b.name:
            text.append(('', b.name + ' '))
            text.append(('reverse', '[' + b.pretty_key + ']'))
            text.append(('', ' | '))

    for b in kb.bindings:
        add_binding(b)

    if get_app().layout.current_window and get_app().layout.current_window.get_key_bindings():
        for b in get_app().layout.current_window.get_key_bindings().bindings:
            add_binding(b)

    windows['bindings_toolbar'].text = text

    newViewport = calculateResultDataViewport()

    prev = windows['result_data'].viewport
    new = {'x': newViewport[0], 'y': newViewport[1]}

    if prev != new:
        windows['result_data'].viewport = new
        windows['result_data'].dirtyCount += 1


allKb = merge_key_bindings(
    [kb, tree.get_keybindings(), queryTabs.get_keybindings(), windows['result_data'].get_keybindings()])

app = Application(
    layout=layout,
    full_screen=True,
    mouse_support=True,
    key_bindings=allKb,
    before_render=before_render
)
app.windows = windows
app.run()
