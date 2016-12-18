# Hello world example. Doesn't depend on any third party GUI framework.
# Tested with CEF Python v55.3+, only on Linux.

from cefpython3 import cefpython as cef
import sys


def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    cef.Initialize()
    cef.CreateBrowserSync(url="https://www.google.com/")
    cef.MessageLoop()
    cef.Shutdown()


def check_versions():
    print("[hello_world.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[hello_world.py] Python {ver}".format(ver=sys.version[:6]))
    assert cef.__version__ >= "55.3", "CEF Python v55.3+ required to run this"


if __name__ == '__main__':
    main()
