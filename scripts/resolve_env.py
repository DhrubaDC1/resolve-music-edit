"""Locate DaVinci Resolve's scripting module on Linux / macOS / Windows and return a connected Resolve object.

Set RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB yourself to override the defaults below.
Requires DaVinci Resolve **Studio** running with Preferences > System > General >
"External scripting using" = Local.
"""
import os, sys, platform

DEFAULTS = {
    "Linux": ("/opt/resolve/Developer/Scripting", "/opt/resolve/libs/Fusion/fusionscript.so"),
    "Darwin": ("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
               "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"),
    "Windows": (os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                             r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"),
                r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"),
}


def _setup():
    api, lib = DEFAULTS.get(platform.system(), DEFAULTS["Linux"])
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    mod = os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules")
    if mod not in sys.path:
        sys.path.insert(0, mod)


def scriptapp():
    _setup()
    try:
        import DaVinciResolveScript as d
    except ImportError as e:
        raise SystemExit(f"Cannot import DaVinciResolveScript ({e}). Set RESOLVE_SCRIPT_API/RESOLVE_SCRIPT_LIB "
                         f"(now {os.environ['RESOLVE_SCRIPT_API']} / {os.environ['RESOLVE_SCRIPT_LIB']}).")
    r = d.scriptapp("Resolve")
    if not r:
        raise SystemExit("Resolve is not reachable: start DaVinci Resolve Studio and set Preferences > System > "
                         "General > External scripting using = Local.")
    return r


if __name__ == "__main__":
    r = scriptapp()
    p = r.GetProjectManager().GetCurrentProject()
    print(r.GetProductName(), r.GetVersionString(), "| project:", p.GetName() if p else None)
