[中文](使用教程.md) | **English**

# TopStar2 Modifier User Guide

Keep the entire folder together. Do not separate or move individual files out of it.

The primary target file is:

`<GameDirectory>\Game\TopStar2_Data\Managed\Assembly-CSharp.dll`

When **Fix Touch & Mouse** is enabled, `PortableWindowsTouch.dll` is also copied automatically to `<GameDirectory>\Game\TopStar2_Data\Managed\`. Song `.pak` files do not need to be touched.

These patches apply to the current version of the game; re-apply them if you reinstall or update the game.

---

## 1. Launching & Auto-Decryption

1. **Completely exit the game** first, then double-click `TopStar2修改器.bat`.
2. The app features a custom frameless immersive titlebar (drag to move, double-click to maximize/restore, with minimize/maximize/close controls). Click **Midnight Luxe / Haute Pearl** to switch between the dual luxury themes (automatically remembered across launches), or click `English` / `中文` to switch the UI language.
3. Click **Browse** to select the **game root directory** (or drag and drop the game folder directly onto the window). The modifier automatically locates `Game\TopStar2_Data\Managed\Assembly-CSharp.dll` and reads the current patch states.
4. **Automatic Decryption of Original Encrypted DLL**: If `Assembly-CSharp.dll` is still the encrypted original, the modifier automatically backs it up to `Assembly-CSharp.dll.bak` (if no backup exists yet), briefly launches `Game\TopStar2.exe` minimized to dump the decrypted DLL from memory, terminates the game process, writes the decrypted DLL to disk, and loads its status.

> Python is required on your PC (the official installer includes Tkinter, so no extra packages are needed). If the console stops with `Python was not found`, install Python with **Add python.exe to PATH** checked and click **Install Now**.

---

## 2. GUI Features

The modifier uses a left category sidebar + right detail card layout powered by `TopStar2Patcher.exe` (`Mono.Cecil.dll`) to inspect and patch `Assembly-CSharp.dll` at the IL level. Every option can be toggled independently, with **Enable Page / Disable Page** shortcuts in the sidebar.

### 1. Songs & Charts

- **Unlock Hard & Master Charts**: Hard no longer requires Normal clear; Master requires no prior clear or mission/achievement.
- **Offline Song Select**: Allows selecting all songs while offline (Versus and matchmaking still require an internet connection).
- **Unlock All Master Charts**: Shows all songs with Master charts in the Master list (difficulties with a star rating `< 0` stay hidden).

### 2. Items & Currency

- **Unlock All Note Types**: Red, green, blue, and arrow notes are all treated as unlocked.
- **Keep Items at 999**: All 18 items stay at 999 when used, and guest/offline usage restrictions are removed.
- **Keep Coins at 99999**: Coins stay at 99999 when spent.
- **Keep Gems at 99999**: Gems stay at 99999 when spent.

### 3. Stage Timers

Toggle an option on to freeze its timer at the entered seconds, or toggle it off to restore the original countdown:

- **Song Select** (`1`–`85`s, default `80`): If greater than `85`, the Play button stays disabled; auto-confirms the highlighted song at `0`.
- **Solo / Versus / Co-op** (`1`–`600`s, default `10`): Auto-selects Solo at `0`.
- **Journey / Mission / Versus** (`1`–`600`s, default `99`): Auto-enters Journey at `0`.
- **Notes & Items** (`1`–`600`s, default `20`): Shared between the Notes and Items steps; auto-advances at `0`.
- **In-Game** (`1`–`999`s, default `90`): Freezes the in-game timer at the entered seconds without timing out; normal stage clear/results still trigger when the chart ends.

### 4. System & Display

- **High Refresh & FPS** (`120Hz` / `240Hz` segmented selector): Disables VSync (`QualitySettings.vSyncCount = 0`) and sets `Application.targetFrameRate` in `PreLoadResource.Start`, and updates `Esc.SetFullScreen` to call `Screen.SetResolution(..., 120/240)` with the selected refresh rate. Because in-game notes, judgment windows, and timers are all driven by real time (`Time.timeSinceLevelLoad` / `AudioSource.time` / `Time.deltaTime`), gameplay speed remains unchanged.
- **Show Built-in FPS**: Initializes the game's built-in `FPSCounter` singleton in `PreLoadResource.Start` to display a persistent `FPS:xxx` overlay at the top-left corner.
- **Fix Touch & Mouse**: Disables cabinet serial/raw touch override and enables Unity mouse & touch input (automatically copies `PortableWindowsTouch.dll` into `Managed`).
- **Bypass IO Check**: Skips startup IO board serial port check; `F1` / `F2` simulate Test / Service keys.
- **Free Play**: Forces Free Play mode so games can start without inserting coins.
- **Skip Tutorial Video**: Skips the tutorial video in Versus, Guest, beginner Journey, and offline startup, going straight to `Song_Select`.
- **Auto-Return to Title Fallback**: Injects a `Time.realtimeSinceStartup`-based fallback into `ContinueControl` that forces `SceneManager.LoadLevel("Title")` if there is no input for 20s or if returning hangs for 4s.

---

## 3. Applying & Reverting

- Toggle any options on or off and click **Apply Changes** in the bottom-right corner.
- Before the first write, `Assembly-CSharp.dll.bak` is created automatically (existing `.bak` files are never overwritten).
- Turn off any option and click **Apply Changes** to revert just that option, or overwrite `Assembly-CSharp.dll` with `Assembly-CSharp.dll.bak` to restore everything at once.
- Restart the game after applying changes.

---

## 4. Manual Hex Reference (Decrypted Unmodified DLL Only)

> The byte offsets below apply only to an **unmodified, decrypted original `Assembly-CSharp.dll`** and are provided for manual reference. For normal use, apply patches through the GUI (`TopStar2Patcher.exe`).

### 1. Unlock Hard & Master Without Clearing

`LockMusicControl.CheckLockType` starts at `0x3A190`:

- `0x3A238` (`0x3A190 + 168`): `18 2A` → `16 2A` (previously returned `2` when Normal was not cleared).
- `0x3A24C` (`0x3A190 + 188`): `19 2A` → `16 2A` (previously returned `3` when Master was locked).

### 2. Allow Song Selection Offline

- `0x3A20A`: `17 2A` → `16 2A` (surrounding bytes `28 5A 04 00 06 3A 02 00 00 00 17 2A`, change only the trailing `17`).

### 3. Show Master Charts in Master List

- Filter starts at `0x3B9D8`; at byte 12 (`0x3B9E4`): `02 7B` → `17 2A`.

### 4. Unlock All Note Types

- `TopStarData.get_OpenAllMusicPermissions` at `0x2ED4`: original `1A 7E D9 02 00 04 2A`, change bytes 2–3 to `17 2A` (`1A 17 2A`).

### 5. Keep Item Inventory at 999

Each 8-byte getter (`1E 02 7B ... 04 2A`) is replaced with `1E 20 E7 03 00 00 2A 00`:

| Offset | Item | Offset | Item |
| --- | --- | --- | --- |
| `0xA3AF` | Single Shield | `0xA448` | Speed 3 |
| `0xA3C0` | Omni Shield | `0xA459` | Speed 4 |
| `0xA3D1` | Time Shield | `0xA46A` | EXP Item A |
| `0xA3E2` | Slow 1 | `0xA47B` | EXP Item B |
| `0xA3F3` | Slow 2 | `0xA48C` | EXP Item C |
| `0xA404` | Slow 3 | `0xA49D` | EXP Item D |
| `0xA415` | Slow 4 | `0xA4AE` | Mirror Horizontal |
| `0xA426` | Speed 1 | `0xA4BF` | Mirror Vertical |
| `0xA437` | Speed 2 | `0xA4D0` | Mirror Both |

### 6. Freeze Song Select Timer at 80s

`MusicSelectControl.Update` (`0x3A677`, 18 bytes):

- Original: `02 25 7B 49 09 00 04 28 5B 00 00 0A 59 7D 49 09 00 04`
- Patched: `02 22 00 00 A0 42 7D 49 09 00 04 00 00 00 00 00 00 00` (must be `<= 85` for the Play button to enable)

### 7. Skip Tutorial Video

Change `"Tutorial"` (`72 97 1B 00 70`) to `"Song_Select"` (`72 6B 07 00 70`) at `0x398E4`, `0x399C6`, `0x3BC6A`, and `0x40990`.

### 8. Freeze In-Game 90s Timer

`TimeLimitManage.get_RemainTimeMs` (`0x2C150`, 39 bytes):

- Original: `02 7B 6A 05 00 04 7E E3 05 00 04 7B E8 05 00 04 59 0A 20 B8 82 01 00 06 28 5F 00 00 0A 0A 06 16 3D 00 00 00 00 06 2A`
- Patched: `20 90 5F 01 00 2A 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`

### 9. Freeze Mode, Note, and Item Timers

| Screen / Method | Offset | Original (18 bytes) | Patched (Default Seconds) |
| --- | --- | --- | --- |
| Solo/Versus/Co-op (`JouneryModeSelect.Update`, 10s) | `0x3290E` | `02 25 7B EB 06 00 04 28 5B 00 00 0A 59 7D EB 06 00 04` | `02 22 00 00 20 41 7D EB 06 00 04 00 00 00 00 00 00 00` |
| Journey/Mission/Versus (`ModeSelect.Update`, 99s) | `0x39812` | `02 25 7B 12 09 00 04 28 5B 00 00 0A 59 7D 12 09 00 04` | `02 22 00 00 C6 42 7D 12 09 00 04 00 00 00 00 00 00 00` |
| Notes & Items (`BuyItemManager.Update`, 20s) | `0x30734` | `02 25 7B 4C 06 00 04 28 5B 00 00 0A 59 7D 4C 06 00 04` | `02 22 00 00 A0 41 7D 4C 06 00 04 00 00 00 00 00 00 00` |
