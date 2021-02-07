from prompt_toolkit.application import get_app
from prompt_toolkit.layout import HSplit, Float
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import Button, TextArea, Dialog, Label


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

    dialog = Dialog(
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

    dialog = Dialog(
        title=title,
        body=HSplit(buttons),
        buttons=[cancel_button],
        width=D(min=50),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().layout.focus(buttons[0])
    get_app().invalidate()


def inputs_dialog(callback, title='', inputs_data=[]):
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

    dialog = Dialog(
        title=title,
        body=HSplit(inputs),
        buttons=[ok_button, cancel_button],
        width=D(min=120),
        with_background=False)

    float_dialog = Float(
        content=dialog
    )

    get_app().layout.container.floats.append(float_dialog)
    get_app().layout.focus(inputs[1])
    get_app().invalidate()
