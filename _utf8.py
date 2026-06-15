import os
import locale

locale.getpreferredencoding = lambda *a, **kw: "UTF-8"
if hasattr(locale, "getencoding"):
    locale.getencoding = lambda *a, **kw: "UTF-8"
os.environ["PYTHONUTF8"] = "1"
