from typing import Callable


class cached_property:
    """A cached property.

    The property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/blob/0.11.5/bottle.py#L175
    """

    def __init__(self, func: Callable):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            # We're being accessed from the class itself, not from an object
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value
