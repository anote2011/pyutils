import mmap

ACCESS_COPY = mmap.ACCESS_COPY
ACCESS_READ = mmap.ACCESS_READ
ACCESS_WRITE = mmap.ACCESS_WRITE


class FileMMap:
    def __init__(self, fd, length, access=0, offset=0):
        self._mm = mmap.mmap(fileno=fd,
                             length=length,
                             access=access,
                             offset=offset)

    def read(self, n=None):
        return self._mm.read(n)

    @property
    def len(self):
        return len(self._mm) - self._mm.tell()

    def __enter__(self):
        self._mm.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._mm.__exit__(exc_type, exc_value, traceback)

    def reset(self):
        self._mm.seek(0, 0)
        return self

