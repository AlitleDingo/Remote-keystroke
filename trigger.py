#!/usr/bin/env python3
"""
Keystroke trigger — run on the Windows 11 PC.

Prompts for either:
  - a keybind in x+y+z form  (e.g. shift+i)
  - txt <text>               (e.g. txt cats  → Mac types c,a,t,s)
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
import os

DEFAULT_PORT = 5055
TIMEOUT_SEC = 8.0

FORMAT_HELP = """
What you can type
-----------------
  1) Keybind (modifiers + key), joined with +  and no spaces:
       shift+i
       ctrl+option+cmd+k
       f9

  2) Type a string of text on the Mac (letter by letter):
       txt cats
       txt Hello world

  Key names for keybinds:
    cmd  or  command   → Command (⌘)
    ctrl or  control   → Control (⌃)
    option or alt      → Option  (⌥)
    shift              → Shift   (⇧)
    a … z, f1 … f12, space, tab, enter, esc

  Type quit to exit.
"""


def send_message(host: str, port: int, payload: bytes, timeout: float) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload)
            reply = b""
            while b"\n" not in reply:
                chunk = sock.recv(64)
                if not chunk:
                    break
                reply += chunk
    except ConnectionRefusedError as exc:
        raise ConnectionError(
            "connection refused — is receiver.py running on the Mac?"
        ) from exc
    except TimeoutError as exc:
        raise ConnectionError(
            "timed out — wrong IP, Mac firewall, or different Wi-Fi network?"
        ) from exc
    except OSError as exc:
        msg = str(exc).lower()
        if "not connected" in msg or getattr(exc, "winerror", None) in (10057, 10054, 10061):
            raise ConnectionError(
                f"{exc}\n"
                "  -> Wrong Mac IP, receiver not running, or Mac firewall blocking port "
                f"{port}.\n"
                "  -> On the Mac, leave receiver.py open and use the IP it prints."
            ) from exc
        raise ConnectionError(str(exc)) from exc

    text = reply.strip().decode("utf-8", errors="replace")
    if text != "OK":
        raise ConnectionError(
            f"Mac replied {reply!r} instead of OK — check receiver.py is the latest version."
        )


def normalize_combo(raw: str) -> str | None:
    text = raw.strip().lower().replace(" ", "")
    if not text:
        return None
    if not re.fullmatch(r"[a-z0-9]+(?:\+[a-z0-9]+)*", text):
        return None
    parts = text.split("+")
    allowed = {
        "cmd", "command", "ctrl", "control", "option", "alt", "shift",
        "win", "super", "space", "tab", "enter", "return", "esc", "escape",
        *list("abcdefghijklmnopqrstuvwxyz"),
        *[f"f{i}" for i in range(1, 13)],
    }
    if any(p not in allowed for p in parts):
        return None
    return "+".join(parts)


def parse_input(raw: str) -> tuple[str, str] | None:
    """
    Returns ("key", combo) or ("txt", text) or ("quit", "") or None if invalid.
    """
    stripped = raw.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    if lower in {"quit", "exit", "q"}:
        return ("quit", "")

    # txt <string>  — keep original casing for the typed text after "txt "
    if lower.startswith("txt ") or lower == "txt":
        text = stripped[4:]  # after "txt "
        if not text:
            return None
        # Cap length so one packet stays small
        if len(text) > 200:
            return None
        return ("txt", text)

    combo = normalize_combo(stripped)
    if combo is None:
        return None
    return ("key", combo)


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        raise SystemExit(0) from None
    except KeyboardInterrupt:
        print("\nBye.")
        raise SystemExit(0) from None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a keybind or text string to the Mac receiver.",
    )
    parser.add_argument("host", nargs="?", help="Mac address (from receiver.py)")
    parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=TIMEOUT_SEC)
    args = parser.parse_args()

    host = args.host
    if not host:
        x = input("Do you want to use the default address for the mac, or do you want to set a new one. D/N: ")
        if x.strip().upper() == "D":
            host = "192.168.1.252"
        else:
            host = ask("Mac address (IP from receiver.py): ").strip()
    if not host:
        print("Need the Mac's address.")
        return 2

    if host in {"127.0.0.1", "localhost"}:
        print("Warning: 127.0.0.1 is THIS PC, not the Mac. Use the Mac's LAN IP.")
    os.system('cls' if os.name == 'nt' else 'clear')
    print(FORMAT_HELP)
    print(f"Mac receiver: {host}:{args.port}")
    print("Type a keybind, or: txt <your text>\n")

    while True:
        raw = ask("> ")
        parsed = parse_input(raw)
        if parsed is None:
            print("Invalid. Examples:  shift+i   |   txt cats   |   quit")
            continue
        kind, value = parsed
        if kind == "quit":
            print("Bye.")
            return 0
        if kind == "key":
            payload = f"KEY:{value}\n".encode("utf-8")
            label = value
        else:
            payload = f"TXT:{value}\n".encode("utf-8")
            label = f'txt "{value}"'

        try:
            send_message(host, args.port, payload, args.timeout)
        except ConnectionError as exc:
            print(f"Could not reach the Mac: {exc}")
            continue
        print(f"Sent: {label}")


if __name__ == "__main__":
    sys.exit(main())
