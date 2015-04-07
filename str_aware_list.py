from collections import Iterable


class StrAwareList(Iterable):
    def __init__(self, output=None):
        if output is None:
            output = []
        self._output = output

    def sep(self):
        self += '\n'
        return self

    def __str__(self):
        if self._output.__class__ == list:
            return '\n'.join(self._output)
        else:
            return str(self._output)

    __repr__ = __str__

    def __len__(self):
        try:
            return getattr(self._output, "__len__")()
        except AttributeError:
            return 0

    def __iter__(self):
        for e in self._output:
            yield e

    def __iadd__(self, other):
        self.__add__(other)
        return self

    def __add__(self, other):
        if isinstance(other, Iterable) and not isinstance(other, str) and not isinstance(other, bytes):
            self._output.extend(other)
            return self
        else:
            self._output.append(other)
            return self
