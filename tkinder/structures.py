import keyword
import _tkinter

from . import _mainloop


class _Config:
    """A view of a widget's options.

    The options can be used like attributes:
        some_label.config.text = "Hello World!"
        print(some_label.config.text)

    Or with a tkinter-style method call:
        some_label.config(text="Hello World!")

    It's also possible to iterate over the options:
        for option, value in some_label.config:
            print(option, value)

    Or you can convert the options to a dictionary:
        the_options = dict(some_label.config)
    """

    def __init__(self, widget):
        self._widget = widget
        self._special_options = {}

    def _set(self, option, value):
        if option in self._special_options:
            setter, getter = self._special_options[option]
            setter(value)
        else:
            _mainloop.tk.call(self._widget.path, 'config', '-' + option, value)

    def _get(self, option):
        if option in self._special_options:
            setter, getter = self._special_options[option]
            return getter()
        return _mainloop.tk.call(self._widget.path, 'cget', '-' + option)

    def __setattr__(self, option, value):
        if option.startswith('_'):
            # it's an attribute from this class, __magic__ or something else
            super().__setattr__(option, value)
            return

        try:
            # the rstrip supports options like from_
            self._set(option.rstrip('_'), value)
        except _tkinter.TclError as error:
            raise AttributeError(str(error)) from None

    def __getattr__(self, option):
        try:
            return self._get(option.rstrip('_'))
        except _tkinter.TclError as error:
            raise AttributeError(str(error)) from None

    def __iter__(self):
        # this doesn't add a '_' because things like setattr() and
        # getattr() work without it too
        for option, (setter, getter) in self._special_options.items():
            yield option, getter()
        for option, *junk in _mainloop.tk.call(self._widget.path, 'config'):
            yield option.lstrip('-'), self._get(option.lstrip('-'))

    def __dir__(self):
        result = []
        for option, value in self:
            if keyword.iskeyword(option):
                # this appends '_' because dir() is meant to be used for
                # debuggy things
                option += '_'
            result.append(option)

        result.sort()
        return result

    def __call__(self, **kwargs):
        if not kwargs:
            # tkinter treats this case specially and it can be confusing
            raise TypeError("config() requires arguments")
        for option, value in kwargs.items():
            self._set(option, value)


class Callback:
    """An object that calls multiple functions.

    >>> c = Callback()
    >>> c.connect(print, "hello")
    >>> c.connect(print, "hello", "again")
    >>> c.run("world")      # usually tkinder does this part
    hello world
    hello again world
    """

    def __init__(self):
        self._connections = []

    def connect(self, function, *extra_args):
        # -1 is this method so -2 is what called this
        stack_info = traceback.format_stack()[-2]
        self._connections.append((function, extra_args, stack_info))

    def disconnect(self, function):
        for index, infotuple in self._connections:
            # can't use is because python makes up method objects dynamically:
            #   >>> class Thing:
            #   ...   def stuff(): pass
            #   ... 
            #   >>> t = Thing()
            #   >>> t.stuff is t.stuff
            #   False
            #   >>> 
            if infotuple[-1] == function:
                del self._connections[index]
                return
        raise ValueError("not connected: %r" % (function,))

    def run(self, *args):
        for func, extra_args, stack_info in self._connections:
            try:
                func(*(extra_args + args))
            except SystemExit as e:
                # unfortunately this doesn't actually exit python, but
                # it's a handy way to end the main loop :)
                if not (isinstance(e.code, int) or e.code is None):
                    print(e.code, file=sys.stderr)
                _mainloop.quit()
                break
            except Exception:
                # display also the connect() call, but run other callbacks
                traceback_blabla, rest = traceback.format_exc().split('\n', 1)
                sys.stderr.write(traceback_blabla + '\n' + stack_info + rest)
