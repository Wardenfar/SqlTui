from __future__ import unicode_literals

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import has_completions, has_focus
from prompt_toolkit.formatted_text import is_formatted_text
from prompt_toolkit.key_binding.bindings.focus import (
    focus_next,
    focus_previous,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Float
from prompt_toolkit.layout.containers import DynamicContainer, HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import Button, TextArea, Label, Shadow, Box, Frame


def remove_float(float):
    if float in get_app().layout.container.floats:
        get_app().layout.container.floats.remove(float)
    get_app().layout.focus(get_app().windows['tree'])


def input_dialog(callback, title='', text='', ok_text='OK', cancel_text='Cancel', completer=None, password=False):
    def ok_handler():
        callback(textfield.text)
        return_handle()

    def return_handle():
        remove_float(float_dialog)
        get_app().invalidate()

    ok_button = Button(text=ok_text, handler=ok_handler)
    cancel_button = Button(text=cancel_text, handler=return_handle)

    textfield = TextArea(
        text="mobius:mobius@localhost:5432",
        multiline=False,
        password=password,
        completer=completer, )

    dialog = CustomDialog(
        title=title,
        body=HSplit([
            Label(text=text, dont_extend_height=True),
            textfield,
        ], padding=D(preferred=1, max=1)),
        buttons=[ok_button, cancel_button],
        width=D(min=120),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().layout.focus(textfield)
    get_app().invalidate()


def merge_handler(h1, h2):
    def merged():
        h1()
        h2()

    return merged


def buttons_dialog(title='', buttons_data=[], cancel_text='Cancel'):
    def return_handle():
        remove_float(float_dialog)
        get_app().invalidate()

    cancel_button = Button(text=cancel_text, handler=return_handle)

    buttons = []
    for data in buttons_data:
        buttons.append(Button(text=data[0], handler=merge_handler(return_handle, data[1]), width=len(data[0]) + 2))

    dialog = CustomDialog(
        title=title,
        body=HSplit(buttons),
        buttons=[cancel_button],
        width=D(min=120),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().layout.focus(buttons[0])
    get_app().invalidate()


def inputs_dialog(callback, title='', subtitle='', inputs_data=[]):
    def ok_handler():
        result = {}
        index = 0
        for i in inputs:
            if isinstance(i, TextArea):
                result[inputs_data[index]] = i.text
                index += 1
        return_handle()
        callback(result)

    def return_handle():
        remove_float(float_dialog)
        get_app().invalidate()

    ok_button = Button(text='Ok', handler=ok_handler)
    cancel_button = Button(text='Cancel', handler=return_handle)

    inputs = []
    for data in inputs_data:
        inputs.append(Label(data))
        inputs.append(TextArea())

    dialog = CustomDialog(
        title=title,
        body=HSplit([Label(subtitle), Label('')] + inputs),
        buttons=[ok_button, cancel_button],
        width=D(min=120),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().layout.focus(inputs[1])
    get_app().invalidate()


def loading_dialog(title=''):
    dialog = CustomDialog(
        title=title,
        body=HSplit([Label(''), Label('....'), Label('')]),
        width=D(min=120),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().invalidate()
    return float_dialog


class CustomDialog(object):
    """
    Simple dialog window. This is the base for input dialogs, message dialogs
    and confirmation dialogs.

    Changing the title and body of the dialog is possible at runtime by
    assigning to the `body` and `title` attributes of this class.

    :param body: Child container object.
    :param title: Text to be displayed in the heading of the dialog.
    :param buttons: A list of `Button` widgets, displayed at the bottom.
    """

    def __init__(self, body, title='', buttons=None, modal=True, width=None,
                 with_background=False):
        assert is_formatted_text(title)
        assert buttons is None or isinstance(buttons, list)

        self.body = body
        self.title = title

        buttons = buttons or []

        # When a button is selected, handle left/right key bindings.
        buttons_kb = KeyBindings()
        if len(buttons) > 1:
            first_selected = has_focus(buttons[0])
            last_selected = has_focus(buttons[-1])

            buttons_kb.add('left', filter=~first_selected)(focus_previous)
            buttons_kb.add('right', filter=~last_selected)(focus_next)

        if buttons:
            frame_body = HSplit([
                # Add optional padding around the body.
                Box(body=DynamicContainer(lambda: self.body),
                    padding=D(preferred=1, max=1),
                    padding_bottom=0),
                # The buttons.
                Box(body=VSplit(buttons, padding=1, key_bindings=buttons_kb),
                    height=D(min=1, max=3, preferred=3))
            ])
        else:
            frame_body = body

        # Key bindings for whole dialog.
        kb = KeyBindings()
        kb.add('tab', filter=~has_completions)(focus_next)
        kb.add('s-tab', filter=~has_completions)(focus_previous)
        kb.add(Keys.Down, filter=~has_completions)(focus_next)
        kb.add(Keys.Up, filter=~has_completions)(focus_previous)

        frame = Shadow(body=Frame(
            title=lambda: self.title,
            body=frame_body,
            style='class:dialog.body',
            width=(None if with_background is None else width),
            key_bindings=kb,
            modal=modal,
        ))

        if with_background:
            self.container = Box(
                body=frame,
                style='class:dialog',
                width=width)
        else:
            self.container = frame

    def __pt_container__(self):
        return self.container
