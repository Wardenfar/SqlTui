from __future__ import unicode_literals

from functools import partial

import six
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import (
    Condition,
)
from prompt_toolkit.formatted_text import (
    Template,
    is_formatted_text,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
    is_container,
)
from prompt_toolkit.layout.dimension import is_dimension
from prompt_toolkit.widgets import Label
from prompt_toolkit.widgets.base import Border

from tabs import Tabs


class CustomFrame(object):
    """
    Draw a border around any container, optionally with a title text.

    Changing the title and body of the frame is possible at runtime by
    assigning to the `body` and `title` attributes of this class.

    :param body: Another container object.
    :param title: Text to be displayed in the top of the frame (can be formatted text).
    :param style: Style string to be applied to this widget.
    """

    def __init__(self, body, title=None, style='', width=None, height=None,
                 key_bindings=None, modal=False):
        assert is_container(body)
        assert is_formatted_text(title)
        assert isinstance(style, six.text_type)
        assert is_dimension(width)
        assert is_dimension(height)
        assert key_bindings is None or isinstance(key_bindings, KeyBindings)
        assert isinstance(modal, bool)

        self.title = title
        self.body = body
        self.style = style

    def build(self):

        body = self.body
        if isinstance(body, Tabs):
            body = body.container

        color = ('white' if get_app().layout.has_focus(body) else '#333333')
        fill = partial(Window, style='class:frame.border ' + color)
        style = 'class:frame ' + self.style

        top_row_with_title = VSplit([
            fill(width=1, height=1, char=Border.TOP_LEFT),
            fill(char=Border.HORIZONTAL),
            fill(width=1, height=1, char='|'),
            # Notice: we use `Template` here, because `self.title` can be an
            # `HTML` object for instance.
            Label(lambda: Template(' {} ').format(self.title),
                  style='class:frame.label ' + color,
                  dont_extend_width=True),
            fill(width=1, height=1, char='|'),
            fill(char=Border.HORIZONTAL),
            fill(width=1, height=1, char=Border.TOP_RIGHT),
        ], height=1)

        top_row_without_title = VSplit([
            fill(width=1, height=1, char=Border.TOP_LEFT),
            fill(char=Border.HORIZONTAL),
            fill(width=1, height=1, char=Border.TOP_RIGHT),
        ], height=1)

        @Condition
        def has_title():
            return bool(self.title)

        return HSplit([
            ConditionalContainer(
                content=top_row_with_title,
                filter=has_title),
            ConditionalContainer(
                content=top_row_without_title,
                filter=~has_title),
            VSplit([
                fill(width=1, char=Border.VERTICAL),
                DynamicContainer(lambda: self.body),
                fill(width=1, char=Border.VERTICAL),
                # Padding is required to make sure that if the content is
                # too small, the right frame border is still aligned.
            ], padding=0),
            VSplit([
                fill(width=1, height=1, char=Border.BOTTOM_LEFT),
                fill(char=Border.HORIZONTAL),
                fill(width=1, height=1, char=Border.BOTTOM_RIGHT),
            ]),
        ], style=style)

    def __pt_container__(self):
        return DynamicContainer(self.build)
