from __future__ import unicode_literals

from prompt_toolkit.filters import Never, to_filter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_bindings import _check_and_expand_key, _Binding


class CustomKeyBindings(KeyBindings):

    def add(self, *keys, **kwargs):
        name = keys[0]
        pretty_key = keys[1]
        keys = keys[2:]

        filter = to_filter(kwargs.pop('filter', True))
        eager = to_filter(kwargs.pop('eager', False))
        is_global = to_filter(kwargs.pop('is_global', False))
        save_before = kwargs.pop('save_before', lambda e: True)
        record_in_macro = to_filter(kwargs.pop('record_in_macro', True))

        assert not kwargs
        assert keys
        assert callable(save_before)

        keys = tuple(_check_and_expand_key(k) for k in keys)

        if isinstance(filter, Never):
            # When a filter is Never, it will always stay disabled, so in that
            # case don't bother putting it in the key bindings. It will slow
            # down every key press otherwise.
            def decorator(func):
                return func
        else:
            def decorator(func):
                if isinstance(func, _Binding):
                    # We're adding an existing _Binding object.
                    self.bindings.append(
                        _Binding(
                            keys, func.handler,
                            filter=func.filter & filter,
                            eager=eager | func.eager,
                            is_global=is_global | func.is_global,
                            save_before=func.save_before,
                            record_in_macro=func.record_in_macro))
                else:
                    self.bindings.append(
                        _Binding(keys, func, filter=filter, eager=eager,
                                 is_global=is_global, save_before=save_before,
                                 record_in_macro=record_in_macro))

                self.bindings[-1].name = name
                self.bindings[-1].pretty_key = pretty_key

                self._clear_cache()

                return func
        return decorator
