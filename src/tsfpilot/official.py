"""Import from the pinned official PatchCore code (third_party/patchcore, commit fcaa92f; section 6)."""
import importlib
import os
import sys

from .config import REPO

PATH = os.path.join(REPO, "third_party", "patchcore")


def module(name):
    """patchcore.<name> from the pinned copy. Refuses a same-named package installed elsewhere."""
    if PATH not in sys.path:
        sys.path.insert(0, PATH)
    mod = importlib.import_module(f"patchcore.{name}")
    if not os.path.abspath(mod.__file__).startswith(PATH + os.sep):
        raise ImportError(f"patchcore.{name} resolved to {mod.__file__}, not the pinned copy in {PATH}")
    return mod
