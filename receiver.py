#!/usr/bin/env python3
"""
Keystroke receiver — run on the Mac (where Raycast lives).

Messages from Windows:
  KEY:shift+i     → press that hotkey once
  TXT:cats        → type c, a, t, s with a short gap between keys
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5055
TYPE_INTERVAL = 0.06  # seconds between letters for TXT:

MAC_MODS = {
    "ctrl": "control down",
    "control": "control down",
    "alt": "option down",
    "option": "option down",
    "shift": "shift down",
    "cmd": "command down",
    "command": "command down",
    "win": "command down",
    "super": "command down",
}

F_CODES = {
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}

SPECIAL = {
    "space": " ",
    "tab": "\t",
    "enter": "return",
    "return": "return",
    "esc": "escape",
    "escape": "escape",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def local_ips() -> list[str]:
    ips: list[str] = []
    for iface in ("en0", "en1"):
        try:
            out = subprocess.check_output(
                ["ipconfig", "getifaddr", iface],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if out and out not in ips:
                ips.append(out)
        except Exception:
            pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip not in ips and not ip.startswith("127."):
            ips.append(ip)
    except Exception:
        pass
    return ips


def run_osascript(script: str) -> None:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "osascript failed").strip()
        raise RuntimeError(err)


def parse_combo(combo: str) -> list[str]:
    return [part.strip().lower() for part in combo.split("+") if part.strip()]


def send_mac_combo(parts: list[str]) -> None:
    mods = [MAC_MODS[p] for p in parts if p in MAC_MODS]
    keys = [p for p in parts if p not in MAC_MODS]
    key = keys[-1] if keys else "c"
    using = f" using {{{', '.join(mods)}}}" if mods else ""

    if key in F_CODES:
        script = f'tell application "System Events" to key code {F_CODES[key]}{using}'
    elif key in SPECIAL:
        special = SPECIAL[key]
        if special in {"return", "escape"}:
            code = 36 if special == "return" else 53
            script = f'tell application "System Events" to key code {code}{using}'
        else:
            ch = special.replace("\\", "\\\\").replace('"', '\\"')
            script = f'tell application "System Events" to keystroke "{ch}"{using}'
    else:
        letter = key[:1] if key else "c"
        letter = letter.replace("\\", "\\\\").replace('"', '\\"')
        script = f'tell application "System Events" to keystroke "{letter}"{using}'

    run_osascript(script)


def fire_keystrokes(combo: str) -> None:
    parts = parse_combo(combo)
    if not parts:
        raise ValueError("empty keybind")
    log(f"  keystrokes: {combo}")
    send_mac_combo(parts)
    time.sleep(0.05)


def type_text(text: str, interval: float = TYPE_INTERVAL) -> None:
    """Type each character with a short pause (for TXT: messages)."""
    log(f'  typing {len(text)} character(s): {text!r}')
    for ch in text:
        if ch == "\n" or ch == "\r":
            run_osascript('tell application "System Events" to key code 36')
        elif ch == "\t":
            run_osascript('tell application "System Events" to keystroke tab')
        else:
            # Escape for AppleScript string
            esc = ch.replace("\\", "\\\\").replace('"', '\\"')
            run_osascript(f'tell application "System Events" to keystroke "{esc}"')
        time.sleep(interval)


def handle_client(conn: socket.socket, addr: tuple) -> None:
    conn.settimeout(8.0)
    action: str | None = None
    value: str = ""
    try:
        buf = b""
        while b"\n" not in buf and len(buf) < 512:
            chunk = conn.recv(256)
            if not chunk:
                break
            buf += chunk
        line = buf.strip().split(b"\n", 1)[0].split(b"\r", 1)[0]
        text = line.decode("utf-8", errors="replace")

        upper = text.upper()
        if upper.startswith("KEY:"):
            action = "key"
            value = text[4:].strip().lower().replace(" ", "")
        elif upper.startswith("TXT:"):
            action = "txt"
            value = text[4:]  # keep spaces and casing after TXT:
            if value.startswith(" "):
                value = value[1:]
        elif upper == "FIRE":
            action = "key"
            value = "shift+i"
        else:
            try:
                conn.sendall(b"NO\n")
            except OSError:
                pass
            log(f"ignored {addr[0]} (bad message: {text!r})")
            return

        if action == "key" and not value:
            try:
                conn.sendall(b"NO\n")
            except OSError:
                pass
            log(f"ignored {addr[0]} (empty keybind)")
            return
        if action == "txt" and value == "":
            try:
                conn.sendall(b"NO\n")
            except OSError:
                pass
            log(f"ignored {addr[0]} (empty text)")
            return

        try:
            conn.sendall(b"OK\n")
            time.sleep(0.05)
        except OSError as exc:
            log(f"could not confirm to {addr[0]}: {exc}")
            return
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            conn.close()
        except OSError:
            pass

    if action is None:
        return

    log(f"trigger from {addr[0]} — {action}: {value!r}")
    try:
        if action == "key":
            fire_keystrokes(value)
        else:
            type_text(value)
    except Exception as exc:
        log(f"  error: {exc}")
        log("  Tip: System Settings → Privacy & Security → Accessibility")
        log("       allow Terminal (or your Python app) to control the computer.")
    log("ready for next trigger")


def serve(host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        log(f"Could not bind {host}:{port} — {exc}")
        log("Is another receiver already running?")
        raise SystemExit(1) from None
    sock.listen(8)

    ips = local_ips()
    log(f"Keystroke receiver listening on port {port}")
    if ips:
        log("On Windows run ONE of these:")
        for ip in ips:
            log(f"  python trigger.py {ip}")
    else:
        log("Could not detect this Mac's IP.")
        log("  python trigger.py <this-mac-ip>")
    log("Accepts KEY:x+y+z and TXT:your text")
    log("Leave this window open. Ctrl+C to stop.\n")

    try:
        while True:
            conn, addr = sock.accept()
            log(f"connection from {addr[0]}:{addr[1]}")
            try:
                handle_client(conn, addr)
            except Exception as exc:
                log(f"client error: {exc}")
    except KeyboardInterrupt:
        print("\nBye.")
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Listen for Windows keybind/text messages and inject Mac keystrokes.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
