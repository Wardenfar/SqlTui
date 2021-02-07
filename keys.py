from __future__ import unicode_literals

from prompt_toolkit.key_binding import KeyBindings


class CustomKeyBindings(KeyBindings):

    def add(self, *keys, **kwargs):
        name = keys[0]
        pretty_key = keys[1]
        keys = keys[2:]

        decorator = super().add(*keys, **kwargs)

        def super_decorator(func):
            tmp = decorator(func)
            self.bindings[-1].name = name
            self.bindings[-1].pretty_key = pretty_key
            return tmp

        return super_decorator
