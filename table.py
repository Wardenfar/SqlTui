#!/usr/bin/env python3
from math import floor

from prompt_toolkit.application import get_app
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import DynamicContainer
# from prompt_toolkit.widgets.base import Border
from prompt_toolkit.layout.containers import Window, VSplit, HSplit, HorizontalAlign, VerticalAlign
from prompt_toolkit.layout.dimension import Dimension as D, sum_layout_dimensions, max_layout_dimensions, to_dimension
from prompt_toolkit.utils import take_using_weights
from prompt_toolkit.widgets import Label


class SpaceBorder:
    """ Box drawing characters. (Spaces) """
    HORIZONTAL = ' '
    VERTICAL = ' '

    TOP_LEFT = ' '
    TOP_RIGHT = ' '
    BOTTOM_LEFT = ' '
    BOTTOM_RIGHT = ' '

    LEFT_T = ' '
    RIGHT_T = ' '
    TOP_T = ' '
    BOTTOM_T = ' '

    INTERSECT = ' '


class AsciiBorder:
    """ Box drawing characters. (ASCII) """
    HORIZONTAL = '-'
    VERTICAL = '|'

    TOP_LEFT = '+'
    TOP_RIGHT = '+'
    BOTTOM_LEFT = '+'
    BOTTOM_RIGHT = '+'

    LEFT_T = '+'
    RIGHT_T = '+'
    TOP_T = '+'
    BOTTOM_T = '+'

    INTERSECT = '+'


class ThinBorder:
    """ Box drawing characters. (Thin) """
    HORIZONTAL = '\u2500'
    VERTICAL = '\u2502'

    TOP_LEFT = '\u250c'
    TOP_RIGHT = '\u2510'
    BOTTOM_LEFT = '\u2514'
    BOTTOM_RIGHT = '\u2518'

    LEFT_T = '\u251c'
    RIGHT_T = '\u2524'
    TOP_T = '\u252c'
    BOTTOM_T = '\u2534'

    INTERSECT = '\u253c'


class RoundedBorder(ThinBorder):
    """ Box drawing characters. (Rounded) """
    TOP_LEFT = '\u256d'
    TOP_RIGHT = '\u256e'
    BOTTOM_LEFT = '\u2570'
    BOTTOM_RIGHT = '\u256f'


class ThickBorder:
    """ Box drawing characters. (Thick) """
    HORIZONTAL = '\u2501'
    VERTICAL = '\u2503'

    TOP_LEFT = '\u250f'
    TOP_RIGHT = '\u2513'
    BOTTOM_LEFT = '\u2517'
    BOTTOM_RIGHT = '\u251b'

    LEFT_T = '\u2523'
    RIGHT_T = '\u252b'
    TOP_T = '\u2533'
    BOTTOM_T = '\u253b'

    INTERSECT = '\u254b'


class DoubleBorder:
    """ Box drawing characters. (Thin) """
    HORIZONTAL = '\u2550'
    VERTICAL = '\u2551'

    TOP_LEFT = '\u2554'
    TOP_RIGHT = '\u2557'
    BOTTOM_LEFT = '\u255a'
    BOTTOM_RIGHT = '\u255d'

    LEFT_T = '\u2560'
    RIGHT_T = '\u2563'
    TOP_T = '\u2566'
    BOTTOM_T = '\u2569'

    INTERSECT = '\u256c'


class Merge:
    def __init__(self, cell, merge=1):
        self.cell = cell
        self.merge = merge

    def __iter__(self):
        yield self.cell
        yield self.merge


class Table(HSplit):
    def __init__(self, table,
                 borders=ThinBorder, column_width=None, column_widths=[],
                 window_too_small=None, align=VerticalAlign.JUSTIFY,
                 padding=0, padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style='', selected=(-1, -1)):
        self.selected = selected
        self.borders = borders
        self.column_width = column_width
        self.column_widths = column_widths

        # ensure the table is iterable (has rows)
        if not isinstance(table, list):
            table = [table]
        children = [_Row(row=row, table=self, borders=borders, ypos=index)
                    for index, row in enumerate(table)]

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    @property
    def columns(self):
        return max(row.raw_columns for row in self.children)

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """

        def get():
            result = []

            # Padding top.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.BOTTOM):
                result.append(Window(width=D(preferred=0)))

            # Border top is first inserted in children loop.

            # The children with padding.
            prev = None
            for child in self.children:
                result.append(_Border(
                    prev=prev,
                    next=child,
                    table=self,
                    borders=self.borders))
                result.append(child)
                prev = child

            # Border bottom.
            result.append(_Border(prev=prev, next=None, table=self, borders=self.borders))

            # Padding bottom.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.TOP):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)

    def preferred_dimensions(self, width):
        dimensions = [[]] * self.columns
        for row in self.children:
            assert isinstance(row, _Row)
            j = 0
            for cell in row.children:
                assert isinstance(cell, _Cell)

                if cell.merge != 1:
                    dimensions[j].append(cell.preferred_width(width))

                j += cell.merge

        for i, c in enumerate(dimensions):
            yield D.exact(1)

            try:
                w = self.column_widths[i]
            except IndexError:
                w = self.column_width
            if w is None:  # fitted
                yield max_layout_dimensions(c)
            else:  # fixed or weighted
                yield to_dimension(w)
        yield D.exact(1)


class _VerticalBorder(Window):
    def __init__(self, borders):
        super().__init__(width=1, char=borders.VERTICAL)


class _HorizontalBorder(Window):
    def __init__(self, borders):
        super().__init__(height=1, char=borders.HORIZONTAL)


class _UnitBorder(Window):
    def __init__(self, char):
        super().__init__(width=1, height=1, char=char)


class _BaseRow(VSplit):
    @property
    def columns(self):
        return self.table.columns

    def _divide_widths(self, width):
        """
        Return the widths for all columns.
        Or None when there is not enough space.
        """
        children = self._all_children

        if not children:
            return []

        # Calculate widths.
        dimensions = list(self.table.preferred_dimensions(width))
        preferred_dimensions = [d.preferred for d in dimensions]

        # Sum dimensions
        sum_dimensions = sum_layout_dimensions(dimensions)

        # If there is not enough space for both.
        # Don't do anything.
        if sum_dimensions.min > width:
            return

        # Find optimal sizes. (Start with minimal size, increase until we cover
        # the whole width.)
        sizes = [d.min for d in dimensions]

        child_generator = take_using_weights(
            items=list(range(len(dimensions))),
            weights=[d.weight for d in dimensions])

        i = next(child_generator)

        # Increase until we meet at least the 'preferred' size.
        preferred_stop = min(width, sum_dimensions.preferred)

        while sum(sizes) < preferred_stop:
            if sizes[i] < preferred_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # Increase until we use all the available space.
        max_dimensions = [d.max for d in dimensions]
        max_stop = min(width, sum_dimensions.max)

        while sum(sizes) < max_stop:
            if sizes[i] < max_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # perform merges if necessary
        if len(children) != len(sizes):
            tmp = []
            i = 0
            for c in children:
                if isinstance(c, _Cell):
                    inc = (c.merge * 2) - 1
                    tmp.append(sum(sizes[i:i + inc]))
                else:
                    inc = 1
                    tmp.append(sizes[i])
                i += inc
            sizes = tmp

        return sizes


class _Row(_BaseRow):
    def __init__(self, row, table, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=D.exact(0), padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style='', ypos=-1):
        self.ypos = ypos
        self.table = table
        self.borders = borders

        # ensure the row is iterable (has cells)
        if not isinstance(row, list):
            row = [row]
        children = []
        xpos = 0
        for c in row:
            m = 1
            if isinstance(c, Merge):
                c, m = c
            elif isinstance(c, dict):
                c, m = Merge(**c)
            children.append(_Cell(cell=c, table=table, row=self, merge=m, xpos=xpos))
            xpos += 1

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    @property
    def raw_columns(self):
        return sum(cell.merge for cell in self.children)

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """

        def get():
            result = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=D(preferred=0)))

            # Border left is first inserted in children loop.

            # The children with padding.
            c = 0
            for child in self.children:
                result.append(_VerticalBorder(borders=self.borders))
                result.append(child)
                c += child.merge
            # Fill in any missing columns
            for _ in range(self.columns - c):
                result.append(_VerticalBorder(borders=self.borders))
                result.append(_Cell(cell=None, table=self.table, row=self))

            # Border right.
            result.append(_VerticalBorder(borders=self.borders))

            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)


class _Border(_BaseRow):
    def __init__(self, prev, next, table, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=D.exact(0), padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        assert prev or next
        self.prev = prev
        self.next = next
        self.table = table
        self.borders = borders

        children = [_HorizontalBorder(borders=borders)] * self.columns

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height or 1,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    def has_borders(self, row):
        yield None  # first (outer) border

        if not row:
            # this row is undefined, none of the borders need to be marked
            yield from [False] * (self.columns - 1)
        else:
            c = 0
            for child in row.children:
                yield from [False] * (child.merge - 1)
                yield True
                c += child.merge

            yield from [True] * (self.columns - c)

        yield None  # last (outer) border

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """

        def get():
            result = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=D(preferred=0)))

            def char(i, pc=False, nc=False):
                if i == 0:
                    if self.prev and self.next:
                        return self.borders.LEFT_T
                    elif self.prev:
                        return self.borders.BOTTOM_LEFT
                    else:
                        return self.borders.TOP_LEFT

                if i == self.columns:
                    if self.prev and self.next:
                        return self.borders.RIGHT_T
                    elif self.prev:
                        return self.borders.BOTTOM_RIGHT
                    else:
                        return self.borders.TOP_RIGHT

                if pc and nc:
                    return self.borders.INTERSECT
                elif pc:
                    return self.borders.BOTTOM_T
                elif nc:
                    return self.borders.TOP_T
                else:
                    return self.borders.HORIZONTAL

            # Border left is first inserted in children loop.

            # The children with padding.
            pcs = self.has_borders(self.prev)
            ncs = self.has_borders(self.next)
            for i, (child, pc, nc) in enumerate(zip(self.children, pcs, ncs)):
                result.append(_UnitBorder(char=char(i, pc, nc)))
                result.append(child)

            # Border right.
            result.append(_UnitBorder(char=char(self.columns)))

            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)


class _Cell(HSplit):
    def __init__(self, cell, table, row, merge=1,
                 padding=0, char=None,
                 padding_left=None, padding_right=None,
                 padding_top=None, padding_bottom=None,
                 window_too_small=None,
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style='', xpos=-1):
        self.xpos = xpos
        self.table = table
        self.row = row
        self.merge = merge

        if padding is None:
            padding = D(preferred=0)

        def get(value):
            if value is None:
                value = padding
            return to_dimension(value)

        self.padding_left = get(padding_left)
        self.padding_right = get(padding_right)
        self.padding_top = get(padding_top)
        self.padding_bottom = get(padding_bottom)

        children = []
        children.append(Window(width=self.padding_left, char=char))
        if cell:
            children.append(cell)
        children.append(Window(width=self.padding_right, char=char))

        children = [
            Window(height=self.padding_top, char=char),
            VSplit(children),
            Window(height=self.padding_bottom, char=char),
        ]

        x = self.xpos
        y = self.row.ypos
        if table.selected[0] == x and table.selected[1] == y:
            style = 'reverse ' + style

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)


class DynamicTable:

    def __init__(self, data=None, viewport=(4, 7), header=[], max=(0, 0)):
        self.header = header
        self.offset = {'x': 0, 'y': 0}
        self.viewport = {'x': viewport[0], 'y': viewport[1]}
        self.max = {'x': max[0], 'y': max[1]}
        self.data = data
        self.cache = SimpleCache(1)
        self.container = DynamicContainer(
            self.get_table_cache
        )
        self.dirtyCount = 0

    def reset(self, data, viewport=(4, 7), header=[], max=(0, 0)):
        self.header = header
        self.offset = {'x': 0, 'y': 0}
        self.viewport = {'x': viewport[0], 'y': viewport[1]}
        self.max = {'x': max[0], 'y': max[1]}
        self.data = data
        self.dirtyCount += 1

    def move_offset(self, x, y):
        self.offset['x'] += x
        self.offset['y'] += y
        self.offset['x'] = max(0, min(self.offset['x'], self.max['x'] - 1))
        self.offset['y'] = max(0, min(self.offset['y'], self.max['y'] - 1))
        self.dirtyCount += 1
        get_app().invalidate()

    def get_keybindings(self):
        kb = KeyBindings()

        @kb.add(Keys.Down)
        def down(event):
            self.move_offset(0, 1)

        @kb.add(Keys.Up)
        def up(event):
            self.move_offset(0, -1)

        @kb.add(Keys.Left)
        def left(event):
            self.move_offset(-1, 0)

        @kb.add(Keys.Right)
        def right(event):
            self.move_offset(1, 0)

        return kb

    def get_table_cache(self):
        return self.cache.get(self.dirtyCount, self.get_table)

    def get_table(self):
        if self.data is None:
            return Label('No data')

        mid_x = floor((self.viewport['x'] - 1) / 2)
        mid_y = floor((self.viewport['y'] - 1) / 2)

        off_x = max(0, min(self.offset['x'] - mid_x, self.max['x'] - self.viewport['x']))
        off_y = max(0, min(self.offset['y'] - mid_y, self.max['y'] - self.viewport['y']))

        rows = self.data[off_y:off_y + self.viewport['y']]
        rows.insert(0, self.header)
        sub = [row[off_x:off_x + self.viewport['x']] for row in rows]

        return Table(
            selected=(self.offset['x'] - off_x, self.offset['y'] - off_y + 1),
            table=sub,
            column_width=D(weight=1),  # D.exact(25),
            column_widths=[],
            borders=ThinBorder)