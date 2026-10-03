# ⟦ CyberTaskManager ⟧ — v6 (Linux/Windows)

Fullscreen cyberpunk Task Manager, residing in the system tray, activatable with the shortcut **Win + Ctrl + T**. Version adapted from scratch for Linux/Arch starting from the original Windows build: same interface and same features, but with system mechanisms (global shortcut, automatic startup, Wi-Fi, sensors) replaced by their native Linux equivalents.

Technical stack: **Python 3.11+ / PySide6 (Qt6) / PyOpenGL / psutil / nvidia-ml-py / soundcard / numpy**.

---

## 0. Main Differences Compared to the Windows Version

| Feature | Windows | Linux (This Build) |
| --- | --- | --- |
| Global shortcut | Automatically registered by the app | Must be linked MANUALLY in your desktop settings (Section 4) |
| Automatic startup | Windows Registry | `.desktop` file in `~/.config/autostart/` |
| Wi-Fi | `netsh` | `nmcli` (NetworkManager), fallback `iw` |
| Temperatures/fans | Requires LibreHardwareMonitor + admin | `lm-sensors`, works WITHOUT elevated privileges |
| Non-NVIDIA GPU | Name via WMI | Name via `lspci` |
| Launcher without terminal | `avvia.bat` | `avvia.sh` |

---

## 1. Prerequisites (Arch Linux System Packages)

Open a terminal and run:

```bash
sudo pacman -Syu
sudo pacman -S python python-pip base-devel mesa glu qt6-base \
    xcb-util-cursor lm_sensors networkmanager iw

```

What each package is for:

* `python`: on Arch, it already includes the `venv` module in the standard library (no separate package needed like on other distros).
* `base-devel`: compilation tools, for the few Python dependencies that need them (equivalent to "build-essential").
* `mesa`, `glu`: system OpenGL/GLU libraries, required for the 3D model.
* `qt6-base`: brings all the xcb/Qt6 libraries needed by the graphical interface (especially useful on minimal Arch installations or with DIY window managers where they might be missing).
* `xcb-util-cursor`: required by the Qt6 XCB plugin.
* `lm_sensors`: to read CPU/GPU temperatures (see Section 5).
* `networkmanager`: for Wi-Fi status via `nmcli` (if you use another network manager like `iwd` or `netctl`, that's fine too: the app automatically uses `iw` as an alternative, see below).
* `iw`: generic Wi-Fi query tool, used as a fallback when NetworkManager is not the active network manager.

---

## 2. Installation

```bash
# Extract the zip into a folder, then enter it, for example:
cd ~/CyberTaskManager

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

Test that it works:

```bash
python3 main.py

```

If the icon appears in the system tray without console errors, everything is okay. Close with "Exit completely" from the tray menu before proceeding.

> **GNOME Note**: Vanilla GNOME hides system tray icons unless you install the **"AppIndicator and KStatusNotifierItem Support"** extension from [extensions.gnome.org](https://extensions.gnome.org/extension/615/appindicator-support/). Without it, the app still works (window, hotkey, everything) but you won't see the icon at the bottom right. On KDE/XFCE/Cinnamon nothing is needed.

---

## 3. Launching Without a Terminal

```bash
chmod +x avvia.sh    # one-time, if the execution permission is not already set
./avvia.sh

```

To launch it with a double click from the file manager or application menu, create a menu launcher (optional but convenient):

```bash
# Replace the path with the actual path of your folder
sed "s#/PATH/COMPLETE/CyberTaskManager#$(pwd)#" cybertaskmanager.desktop.template \
    > ~/.local/share/applications/cybertaskmanager.desktop

```

From this moment on, "CyberTaskManager" also appears in your desktop's application menu, launchable without a terminal.

---

## 4. Global Shortcut Win + Ctrl + T (IMPORTANT Step)

Unlike Windows, here the combination must be manually linked in system settings, pointing it to this command:

```
/PATH/COMPLETE/CyberTaskManager/venv/bin/python3 /PATH/COMPLETE/CyberTaskManager/main.py --toggle

```

(replace `/PATH/COMPLETE/` with the real path, e.g., `/home/micky/CyberTaskManager`)

This command does not open a new window: it tells the one already running in the tray to show/hide. **The app must already be running** (with `avvia.sh` or from the menu) for the shortcut to work — exactly like on Windows.

### On GNOME

DISCLAIMER: ('make sure the app indicator works. otherwise download with>
sudo apt install gnome-shell-extension-manager,
sudo apt install gnome-shell-extension-appindicator.
then select the app extension and enable the appindicator('

1. Settings → Keyboard → Custom Keyboard Shortcuts → "+" (or "View More" → "Custom Shortcuts").
2. Name: `CyberTaskManager Toggle`.
3. Command: paste the line above (with your paths).
4. Set shortcut: press the Win, Ctrl, and T keys together when prompted.

### On KDE Plasma

System Settings → Shortcuts → Custom Shortcuts → Edit → New → Global Command/URL, paste the command and assign the combination.

### On XFCE

Settings → Keyboard → Application Shortcuts → Add, paste the command and press the combination.

---

## 5. Hardware Sensors: Temperatures and Fans

On Linux, this works better than on Windows, and WITHOUT administrator privileges:

```bash
sudo apt install lm-sensors
sudo sensors-detect    # answer "yes" (or Enter, the default) to all questions
sensors                # verify that it prints real temperatures

```

Once `lm-sensors` is configured, the app automatically reads temperatures via `psutil` — no additional configuration inside the app itself. Fans are read the same way if the motherboard exposes them (not all models/drivers expose them on Linux).

---

## 6. Audio: Microphone and System Audio

The `soundcard` library works on Linux via **PulseAudio** or **PipeWire** (with the PulseAudio compatibility layer, installed by default if you use PipeWire or PulseAudio with GNOME). If the "SYSTEM (OUTPUT)" panel remains flat, check that the audio service is active:

```bash
pactl info    # must reply with server information, not an error

```

---

## 7. Wi-Fi

Works automatically if the system uses **NetworkManager** via the `nmcli` command. On minimal installations without NetworkManager, the app automatically tries `iw` as a fallback. If you are connected via Ethernet cable, the panel correctly displays "Not connected" (this is expected behavior, it only concerns Wi-Fi).

---

## 8. Automatic Startup at Login

Open the app settings (tray menu → Settings...) and check "Start automatically at login": this writes a `.desktop` file to `~/.config/autostart/`, the XDG standard respected by all major Linux desktops. No administrative permissions required.

---

## 9. Wayland vs X11

Some window functions (always on top, forced fullscreen positioning) are more reliable on **X11** than on **Wayland**, due to security restrictions imposed by Wayland on compositors. If you notice weirdness with the fullscreen window or with the window not staying on top, try logging in by choosing "GNOME on Xorg" (or your display manager's equivalent) from the login screen (gear icon near the sign-in button).

---

## 10. Compiling Into a Standalone Executable

```bash
pip install pyinstaller
pyinstaller build_exe.spec

```

Executable is in `dist/CyberTaskManager/CyberTaskManager` (Linux ELF, no console). Update `avvia.sh` or the `.desktop` file to point there instead of `main.py` if you prefer to distribute only the compiled executable.

---

## 11. Security and Privacy Notes

* No data leaves the PC: hardware, audio, and Wi-Fi remain local.
* The hotkey mechanism uses only a local pidfile and a standard Unix signal (SIGUSR1): no global keyboard hook, no special permissions required.
* Audio levels are numbers (0-100%), never saved recordings.

---

## 12. Quick Troubleshooting

| Problem | Probable Cause | Solution |
| --- | --- | --- |
| Don't see icon in system tray | GNOME without AppIndicator extension | Section 2 — app still works, only the icon is missing |
| Win+Ctrl+T does nothing | Shortcut not configured, or app not running | Section 4 — app must already be running |
| `ModuleNotFoundError` on startup | Dependencies not installed in the active venv | `source venv/bin/activate` then `pip install -r requirements.txt` |
| Temperatures always "off" | `lm-sensors` not configured | Section 5 |
| System audio flat | PulseAudio/PipeWire not active | Section 6 |
| Wi-Fi "Not connected" but you are online | You are on Ethernet, or NetworkManager is not managing the interface | Expected behavior in the first case; in the second verify `nmcli dev status` |
| Fullscreen window behaves strangely | Wayland session | Try with "GNOME on Xorg" (Section 9) |
| Want to close the app completely | ESC/window close only hides it | "Exit completely" from the system tray menu |
