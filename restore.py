#!/usr/bin/env python3
"""Remove the "Restart" item from the DeepSeek Harness tray menu.

Copies app.asar.bak-tray back over app.asar. The backup is created by patch.py
on first run, so this only works if you patched before.
"""

import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_asar():
    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(
            os.path.join(local, "Programs", "DeepSeek Harness", "resources", "app.asar")
        )
    pf = os.environ.get("ProgramFiles")
    if pf:
        candidates.append(os.path.join(pf, "DeepSeek Harness", "resources", "app.asar"))
    if len(sys.argv) > 1:
        candidates.insert(0, sys.argv[1])
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def main():
    asar = find_asar()
    if not asar:
        print("[x] app.asar not found.")
        return 1

    folder = os.path.dirname(asar)
    backups = sorted(f for f in os.listdir(folder) if f.startswith("app.asar.bak-tray"))
    if not backups:
        print("[x] No backup found (app.asar.bak-tray).")
        print("    Either it was never patched, or the backup was deleted.")
        return 1

    bak = os.path.join(folder, backups[0])
    try:
        shutil.copyfile(bak, asar)
    except PermissionError:
        print("[x] app.asar is locked - quit DeepSeek Harness from the tray, then rerun.")
        return 1
    except Exception as exc:
        print("[x] Restore failed: %s" % exc)
        return 1

    print("[+] Restored from " + backups[0])
    print("    Reopen DeepSeek Harness; the tray menu is back to stock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
