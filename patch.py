#!/usr/bin/env python3
"""Add a "Restart" item to the DeepSeek Harness system tray menu.

Why a patch is needed: the tray is an Electron main-process object, and plugins
live in the renderer, so they cannot touch it. The only way in is to edit the
DesktopTray implementation inside resources/app.asar.

What this script does:
  1. Locate app.asar (default: %LOCALAPPDATA%\\Programs\\DeepSeek Harness\\resources)
  2. Extract lib/main.js and make two exact replacements. If either anchor does
     not match exactly once, the version is incompatible and we bail out safely.
  3. Re-lay out every file offset in physical order and recompute integrity.
  4. Self-check: reparse the new archive and confirm the patch is really there.
  5. Back up the original as app.asar.bak-tray on first run, then swap it in.

Output is ASCII-only on purpose: Windows consoles may be GBK, and mojibake in
an error message is worse than plain English.
"""

import hashlib
import json
import os
import struct
import sys

MARK = 'messages.restartApplication ?? "重启"'

REPLACEMENTS = [
    (
        "tray menu item",
        '\t\t\t{ type: "separator" },\n'
        "\t\t\t{\n"
        "\t\t\t\tlabel: messages.quitApplication,",
        '\t\t\t{ type: "separator" },\n'
        "\t\t\t{\n"
        '\t\t\t\tlabel: messages.restartApplication ?? "重启",\n'
        "\t\t\t\tclick: () => {\n"
        "\t\t\t\t\tthis.options.restart?.();\n"
        "\t\t\t\t}\n"
        "\t\t\t},\n"
        "\t\t\t{\n"
        "\t\t\t\tlabel: messages.quitApplication,",
    ),
    (
        "tray instantiation",
        "\t\t\tquit: () => {\n"
        "\t\t\t\tapp.quit();\n"
        "\t\t\t}\n"
        "\t\t});",
        "\t\t\tquit: () => {\n"
        "\t\t\t\tapp.quit();\n"
        "\t\t\t},\n"
        "\t\t\trestart: () => {\n"
        "\t\t\t\tapp.relaunch();\n"
        "\t\t\t\tapp.exit(0);\n"
        "\t\t\t}\n"
        "\t\t});",
    ),
]


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


def parse(buf):
    """Return (tree, files, base); files is [(path, node)] with nodes shared by tree."""
    # asar header: [0:4]=4, [4:8]=pickle, [8:12]=json_size, [12:16]=json_len
    pickle_size = struct.unpack("<I", buf[4:8])[0]
    json_len = struct.unpack("<I", buf[12:16])[0]
    base = 8 + pickle_size
    # json_len 是 4 字节对齐后的长度，末尾可能带填充，raw_decode 容忍尾随数据。
    text = buf[16: 16 + json_len].decode("utf-8")
    tree, _ = json.JSONDecoder().raw_decode(text)

    files = []

    def walk(node, path):
        for name, child in node.get("files", {}).items():
            sub = path + "/" + name
            if "files" in child:
                walk(child, sub)
            elif not child.get("unpacked"):
                files.append((sub, child))

    walk(tree, "")
    return tree, files, base


def build(tree, files, main_raw, buf, base):
    target = "/lib/main.js"
    entry = next(n for p, n in files if p == target)

    # 类型必须跟原包一致：offset 是字符串，size 是数字。
    # 把 size 写成字符串会让 Electron 解析出 0 字节，报 "Cannot find module lib/main.js"。
    entry["size"] = len(main_raw)
    if "integrity" in entry:
        digest = hashlib.sha256(main_raw).hexdigest()
        entry["integrity"]["hash"] = digest
        entry["integrity"]["blocks"] = [digest]

    # main.js grew, so everything after it shifts; re-lay out the whole data area.
    files.sort(key=lambda x: int(x[1]["offset"]))
    blobs = []
    pos = 0
    for path, node in files:
        if path == target:
            blob = main_raw
        else:
            off = int(node["offset"])
            size = int(node["size"])
            blob = buf[base + off: base + off + size]
        node["offset"] = str(pos)
        pos += len(blob)
        blobs.append(blob)

    new_json = json.dumps(tree, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pad = (-len(new_json)) % 4
    new_json += b" " * pad
    n = len(new_json)

    # asar header: [4][pickle=json+8][json_size=json+4][json_len][json...]
    head = (
        struct.pack("<I", 4)
        + struct.pack("<I", n + 8)
        + struct.pack("<I", n + 4)
        + struct.pack("<I", n)
    )
    return b"".join([head, new_json] + blobs)


def main():
    asar = find_asar()
    if not asar:
        print("[x] app.asar not found.")
        print("    Expected: %LOCALAPPDATA%\\Programs\\DeepSeek Harness\\resources\\app.asar")
        print('    Installed elsewhere? python patch.py "D:\\path\\to\\app.asar"')
        return 1

    print("[*] Harness: " + asar)
    with open(asar, "rb") as f:
        buf = f.read()

    tree, files, base = parse(buf)
    entry = next((n for p, n in files if p == "/lib/main.js"), None)
    if entry is None:
        print("[x] lib/main.js missing from the archive - unexpected layout, aborted.")
        return 1

    off = int(entry["offset"])
    size = int(entry["size"])
    src = buf[base + off: base + off + size].decode("utf-8")

    if MARK in src:
        print("[=] Already patched, nothing to do.")
        return 0

    for name, old, new in REPLACEMENTS:
        hits = src.count(old)
        if hits != 1:
            print("[x] Anchor not found: %s (matched %d times, expected 1)." % (name, hits))
            print("    This Harness version changed its main-process code. Original untouched.")
            return 1
        src = src.replace(old, new)

    main_raw = src.encode("utf-8")
    print("[*] main.js: %d -> %d bytes (+%d)" % (size, len(main_raw), len(main_raw) - size))

    out = build(tree, files, main_raw, buf, base)

    # Self-check: reparse and confirm the patch really landed.
    try:
        _, f2, b2 = parse(out)
        e2 = next(n for p, n in f2 if p == "/lib/main.js")
        text = out[b2 + int(e2["offset"]): b2 + int(e2["offset"]) + int(e2["size"])].decode("utf-8")
        if MARK not in text or "restart: () => {" not in text:
            print("[x] Self-check failed: patched archive is missing the new code. Aborted.")
            return 1
    except Exception as exc:
        print("[x] Self-check failed: %s. Aborted." % exc)
        return 1

    folder = os.path.dirname(asar)
    backups = [f for f in os.listdir(folder) if f.startswith("app.asar.bak-tray")]
    if not backups:
        bak = os.path.join(folder, "app.asar.bak-tray")
        with open(bak, "wb") as f:
            f.write(buf)
        print("[*] Backup created: app.asar.bak-tray")
    else:
        print("[*] Existing backup kept: " + sorted(backups)[0])

    tmp = asar + ".new"
    with open(tmp, "wb") as f:
        f.write(out)

    try:
        os.replace(tmp, asar)
    except PermissionError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print("[x] app.asar is locked - quit DeepSeek Harness from the tray, then rerun.")
        return 1
    except Exception as exc:
        print("[x] Write failed: %s" % exc)
        return 1

    print("")
    print("[+] Patched. Reopen DeepSeek Harness and right-click the tray icon.")
    print("    Note: app updates overwrite this - just run the installer again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
