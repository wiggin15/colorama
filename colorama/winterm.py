# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
from . import win32


# from wincon.h
class WinColor(object):
    BLACK   = 0
    BLUE    = 1
    GREEN   = 2
    CYAN    = 3
    RED     = 4
    MAGENTA = 5
    YELLOW  = 6
    GREY    = 7

# from wincon.h
class WinStyle(object):
    NORMAL              = 0x00 # dim text, dim background
    BRIGHT              = 0x08 # bright text, dim background
    BRIGHT_BACKGROUND   = 0x80 # dim text, bright background

class WinTerm(object):

    def __init__(self, on_stderr=False):
        self._handle = win32.STDERR if on_stderr else win32.STDOUT
        self._default = win32.GetConsoleScreenBufferInfo(self._handle).wAttributes
        self.set_attrs(self._default)
        self._default_fore = self._fore
        self._default_back = self._back
        self._default_style = self._style
        # In order to emulate LIGHT_EX in windows, we borrow the BRIGHT style.
        # So that LIGHT_EX colors and BRIGHT style do not clobber each other,
        # we track them separately, since LIGHT_EX is overwritten by Fore/Back
        # and BRIGHT is overwritten by Style codes.
        self._light = 0

    def get_attrs(self):
        return self._fore + self._back * 16 + (self._style | self._light)

    def set_attrs(self, value):
        self._fore = value & 7
        self._back = (value >> 4) & 7
        self._style = value & (WinStyle.BRIGHT | WinStyle.BRIGHT_BACKGROUND)

    def reset_all(self):
        self.set_attrs(self._default)
        self.set_console(attrs=self._default)
        self._light = 0

    def fore(self, fore=None, light=False):
        if fore is None:
            fore = self._default_fore
        self._fore = fore
        # Emulate LIGHT_EX with BRIGHT Style
        if light:
            self._light |= WinStyle.BRIGHT
        else:
            self._light &= ~WinStyle.BRIGHT
        self.set_console()

    def back(self, back=None, light=False):
        if back is None:
            back = self._default_back
        self._back = back
        # Emulate LIGHT_EX with BRIGHT_BACKGROUND Style
        if light:
            self._light |= WinStyle.BRIGHT_BACKGROUND
        else:
            self._light &= ~WinStyle.BRIGHT_BACKGROUND
        self.set_console()

    def style(self, style=None):
        if style is None:
            style = self._default_style
        self._style = style
        self.set_console()

    def set_console(self, attrs=None):
        if attrs is None:
            attrs = self.get_attrs()
        win32.SetConsoleTextAttribute(self._handle, attrs)

    def get_position(self):
        position = win32.GetConsoleScreenBufferInfo(self._handle).dwCursorPosition
        # Because Windows coordinates are 0-based,
        # and win32.SetConsoleCursorPosition expects 1-based.
        position.X += 1
        position.Y += 1
        return position

    def set_cursor_position(self, position=None):
        if position is None:
            # I'm not currently tracking the position, so there is no default.
            # position = self.get_position()
            return
        win32.SetConsoleCursorPosition(self._handle, position)

    def cursor_adjust(self, x, y):
        position = self.get_position()
        adjusted_position = (position.Y + y, position.X + x)
        win32.SetConsoleCursorPosition(self._handle, adjusted_position, adjust=False)

    def erase_screen(self, mode=0,):
        # 0 should clear from the cursor to the end of the screen.
        # 1 should clear from the cursor to the beginning of the screen.
        # 2 should clear the entire screen, and move cursor to (1,1)
        csbi = win32.GetConsoleScreenBufferInfo(self._handle)
        # get the number of character cells in the current buffer
        cells_in_screen = csbi.dwSize.X * csbi.dwSize.Y
        # get number of character cells before current cursor position
        cells_before_cursor = csbi.dwSize.X * csbi.dwCursorPosition.Y + csbi.dwCursorPosition.X
        if mode == 0:
            from_coord = csbi.dwCursorPosition
            cells_to_erase = cells_in_screen - cells_before_cursor
        elif mode == 1:
            from_coord = win32.COORD(0, 0)
            cells_to_erase = cells_before_cursor
        elif mode == 2:
            from_coord = win32.COORD(0, 0)
            cells_to_erase = cells_in_screen
        else:
            # invalid mode
            return
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(self._handle, ' ', cells_to_erase, from_coord)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(self._handle, self.get_attrs(), cells_to_erase, from_coord)
        if mode == 2:
            # put the cursor where needed
            win32.SetConsoleCursorPosition(self._handle, (1, 1))

    def erase_line(self, mode=0):
        # 0 should clear from the cursor to the end of the line.
        # 1 should clear from the cursor to the beginning of the line.
        # 2 should clear the entire line.
        csbi = win32.GetConsoleScreenBufferInfo(self._handle)
        if mode == 0:
            from_coord = csbi.dwCursorPosition
            cells_to_erase = csbi.dwSize.X - csbi.dwCursorPosition.X
        elif mode == 1:
            from_coord = win32.COORD(0, csbi.dwCursorPosition.Y)
            cells_to_erase = csbi.dwCursorPosition.X
        elif mode == 2:
            from_coord = win32.COORD(0, csbi.dwCursorPosition.Y)
            cells_to_erase = csbi.dwSize.X
        else:
            # invalid mode
            return
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(self._handle, ' ', cells_to_erase, from_coord)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(self._handle, self.get_attrs(), cells_to_erase, from_coord)

    def set_title(self, title):
        win32.SetConsoleTitle(title)
