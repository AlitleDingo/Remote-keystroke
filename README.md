# Remote-keystroke

## Description

Keystroke Wire is a small local-network tool that lets one computer tell another computer to press keys or type text. The usual setup is a Windows PC as the trigger—where you type commands in a terminal—and a Mac as the receiver, where those keys actually fire. On the Mac, injected keystrokes can open Raycast commands, hit system shortcuts, or type into whatever app is focused.

The project exists to solve a simple problem: you want a deliberate action on one machine (for example a hotkey that Raycast handles, or a short string typed into a field) without walking over to that machine or installing a heavy remote-desktop stack. It uses only Python’s standard library and a plain TCP message format, so there is nothing to install with pip.

What stands out is the split between **hotkeys** (`shift+i`) and **typed text** (`txt cats`), plus a receiver that can keep running in the background with `nohup` so the Mac does not depend on an open Terminal window.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Other Configurations](#other-configurations)
- [Credits](#credits)
- [License](#license)

## Installation

### Requirements

Both machines need **Python 3** and must share the same Wi‑Fi or wired LAN. On Windows, install Python from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH** during setup. On a Mac, run `python3 --version` to confirm Python is available.

Place `trigger.py` on the machine that will send commands (typically Windows) and `receiver.py` on the machine that will receive them (typically a Mac).

### Mac permissions

The receiver injects real keyboard events. On the Mac, open **System Settings → Privacy & Security → Accessibility** and allow **Terminal** (or iTerm, or whichever app runs `python3`). Without that permission, network messages can arrive but no keys will press.

If the Mac firewall is enabled, it may block inbound connections on port **5055**. Open **System Settings → Network → Firewall → Options…** and allow incoming connections for Python or Terminal. For a first test you can turn the firewall off briefly, confirm that Windows connects, then turn it back on and keep an allow rule.

### Start the receiver (Mac)

In Terminal, change into the folder that contains `receiver.py` and run:

```bash
python3 receiver.py
```

The script prints the listening port and the LAN IP address(es) Windows should use. Leave that process running, or use the background method in the Usage section.

### Start the trigger (Windows)

In Command Prompt or PowerShell, change into the folder that contains `trigger.py` and pass the Mac IP printed by the receiver:

```text
python trigger.py 192.168.1.42
```

If `python` is not found, try `py trigger.py 192.168.1.42`. Do not use `127.0.0.1` on Windows; that address is the Windows PC itself, not the Mac.

## Usage

When the trigger starts, it prints a short format guide and then a `>` prompt.

**Send a hotkey** by typing modifiers and a key joined with `+` and no spaces:

```text
> shift+i
> ctrl+option+cmd+k
> f9
```

The Mac presses that combination once. Bind the same shortcut in Raycast (or another app) if you want that press to run a command.

**Type text** by prefixing the string with `txt` and a space:

```text
> txt cats
> txt Hello world
```

The Mac types each character with a short pause between letters. Focus the target text field on the Mac before you send so the characters land in the right place.

**Quit** the trigger with:

```text
> quit
```

### Key names

| You type                       | Meaning on the Mac |
| ------------------------------ | ------------------ |
| `cmd` or `command`             | Command (⌘)        |
| `ctrl` or `control`            | Control (⌃)        |
| `option` or `alt`              | Option (⌥)         |
| `shift`                        | Shift (⇧)          |
| `a` … `z`                      | Letter keys        |
| `f1` … `f12`                   | Function keys      |
| `space`, `tab`, `enter`, `esc` | Special keys       |

### Keep the Mac receiver running after Terminal closes

A normal `python3 receiver.py` session stops when you close Terminal. To keep listening in the background, start the receiver with `nohup` from the folder that contains `receiver.py`:

```bash
nohup python3 receiver.py > receiver.log 2>&1 &
```

`nohup` ignores the hangup signal sent when the terminal closes. Output is written to `receiver.log` so you can still inspect connections. The trailing `&` returns you to the shell immediately.

Useful follow-ups:

```bash
pgrep -fl receiver.py    # confirm it is running
tail -f receiver.log     # watch the log live
pkill -f receiver.py     # stop the receiver later
```

After this, you can quit Terminal entirely. Accessibility permission still applies to the environment that runs Python; if keystrokes stop working after you change how you launch the script, re-check **Privacy & Security → Accessibility**.

### Troubleshooting

If Windows reports that the socket is not connected, the connection was refused, or the attempt timed out, the Mac is not accepting the TCP connection. Confirm that the receiver is still running, that you used the IP printed by `receiver.py`, that both machines are on the same network, and that the Mac firewall allows port 5055.

If the connection succeeds but nothing useful happens on the Mac, verify Accessibility permission first. For hotkeys, match the Raycast (or app) shortcut to what you send. For `txt …`, focus a text field on the Mac before sending. The Mac log—either the Terminal window or `receiver.log`—should show each successful trigger.

## Features

- **Hotkey relay** — send combinations such as `shift+i` or `ctrl+option+cmd+k` for Raycast or system shortcuts  
- **Text typing** — `txt your message` types characters one by one on the receiver  
- **Interactive trigger** — format help at startup, then a simple `>` prompt loop  
- **Stdlib only** — no pip dependencies; Python 3 on each machine is enough  
- **Background receiver** — optional `nohup` workflow so the Mac keeps listening after Terminal closes  
- **Clear network protocol** — lines like `KEY:shift+i` and `TXT:cats` over TCP, with `OK` / `NO` replies

## Other Configurations

The default pair is Windows as trigger and Mac as receiver because the Mac script uses `osascript` and System Events. You can still adapt the same idea elsewhere.

Running the trigger on a Mac works without code changes: `python3 trigger.py <other-ip>`. The protocol does not care which OS sends the message.

Using **Windows as the receiver** requires replacing the Mac-specific key injection in `receiver.py` with Windows APIs (for example `ctypes` and `keybd_event` / `SendInput`, or a library such as `pynput`). The network format (`KEY:…` and `TXT:…`) can stay the same, so Windows-to-Windows or Mac-to-Windows setups are possible once that side exists.

To use another port:

```bash
# Mac
python3 receiver.py --port 5056

# Windows
python trigger.py 192.168.1.42 5056
```

With nohup on a custom port:

```bash
nohup python3 receiver.py --port 5056 > receiver.log 2>&1 &
```

Use this tool only on a trusted private network. There is no password and no encryption; do not expose port 5055 to the public internet.

## Credits

Code written by me, REEDME generated using grok. 



## License

MIT License
Copyright (c) 2026 Alittle Dingo
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
