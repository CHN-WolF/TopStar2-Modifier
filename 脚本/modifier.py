#!/usr/bin/env python3
"""Haute-Couture Frameless Dual-Theme GUI for TopStar2 Modifier.

Themes:
  - dark:  深色奢华版（午夜星河 · Midnight Obsidian, Royal Amethyst & 18K Champagne Gold）
  - light: 浅色高贵版（高定珍珠瓷白 · Haute Pearl, Ivory Bone-China & Royal Iris）
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import io
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import zlib
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

ROOT = Path(__file__).absolute().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import i18n  # noqa: E402
from i18n import t  # noqa: E402

DLL_TAIL = Path("Game") / "TopStar2_Data" / "Managed" / "Assembly-CSharp.dll"
EXE_TAIL = Path("Game") / "TopStar2.exe"
PATCHER_EXE = ROOT / "TopStar2Patcher.exe"
PREFS_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "TopStar2Modifier" / "ui_prefs.json"

HOLDS = (
    {
        "key": "song",
        "title": "选歌",
        "detail": "大于 85 时播放键不亮。到 0 会自动确认当前歌。",
        "default": 80,
        "low": 1,
        "high": 85,
        "places": 0,
    },
    {
        "key": "mode10",
        "title": "单人 / 对战 / 合作",
        "detail": "到 0 会自动选单人。",
        "default": 10,
        "low": 1,
        "high": 600,
        "places": 0,
    },
    {
        "key": "mode99",
        "title": "旅程 / 任务 / 对战",
        "detail": "到 0 会自动进旅程。",
        "default": 99,
        "low": 1,
        "high": 600,
        "places": 0,
    },
    {
        "key": "item",
        "title": "音符和道具",
        "detail": "两步共用这一个倒计时。到 0 会自己进入下一步。",
        "default": 20,
        "low": 1,
        "high": 600,
        "places": 0,
    },
)

PLAY_SPEC = {
    "key": "play",
    "title": "局内",
    "detail": "铺面结束仍会通关结算。",
    "default": 90,
    "low": 1,
    "high": 999,
    "places": 0,
}

FLAGS = (
    {
        "key": "clear",
        "title": "解除高级与大师谱面游玩限制",
        "detail": "高级无需先通关普通；大师无需通关高级或完成成就/任务。",
        "note_on": "已解除高级与大师谱面游玩限制",
        "note_off": "高级与大师谱面游玩限制已还原",
    },
    {
        "key": "offline",
        "title": "离线也能选歌",
        "detail": "对战和找人仍要联网。",
        "note_on": "离线也能选歌",
        "note_off": "离线选歌限制已还原",
    },
    {
        "key": "masterlist",
        "title": "解锁所有大师谱面",
        "detail": "星级小于 0 的难度仍然不出现。",
        "note_on": "已解锁所有大师谱面",
        "note_off": "大师谱面列表过滤已还原",
    },
    {
        "key": "notes",
        "title": "音符全部解锁",
        "detail": "红、绿、蓝、箭头都算已解锁。",
        "note_on": "音符已全部解锁",
        "note_off": "音符解锁已还原",
    },
    {
        "key": "items",
        "title": "道具保持 999",
        "detail": "这 18 个道具用掉也不减少，且解除游客/离线使用限制。",
        "note_on": "道具数量保持 999（已解除使用限制）",
        "note_off": "道具数量与使用限制已还原",
    },
    {
        "key": "coins",
        "title": "金币保持 99999",
        "detail": "消费金币不会减少。",
        "note_on": "金币数量保持 99999",
        "note_off": "金币数量已还原",
    },
    {
        "key": "gems",
        "title": "宝石保持 99999",
        "detail": "消费宝石不会减少。",
        "note_on": "宝石数量保持 99999",
        "note_off": "宝石数量已还原",
    },
)

OTHER_FLAGS = (
    {
        "key": "vsync_off",
        "title": "关闭垂直同步",
        "detail": "强制关闭垂直同步（vSyncCount = 0），降低输入延迟。",
        "note_on": "已强制关闭垂直同步",
        "note_off": "垂直同步设置已还原",
    },
    {
        "key": "fps_display",
        "title": "显示内置 FPS",
        "detail": "在屏幕左上角显示游戏内置 FPS 计数器。",
        "note_on": "已开启内置 FPS 显示",
        "note_off": "内置 FPS 显示已还原",
    },
    {
        "key": "fix_touch",
        "title": "修复触屏与鼠标",
        "detail": "禁用框体串口/原始触摸接管，启用 Unity 鼠标与触屏输入。",
        "note_on": "已修复触屏与鼠标输入",
        "note_off": "触屏与鼠标输入已还原",
    },
    {
        "key": "no_io",
        "title": "去IO检测",
        "detail": "跳过开机 IO 板串口检测，F1/F2 可模拟测试/服务键。",
        "note_on": "已开启去IO检测",
        "note_off": "IO检测已还原",
    },
    {
        "key": "free_play",
        "title": "免费投币",
        "detail": "强制开启免费游玩（Free Play），无需投币即可开始。",
        "note_on": "已开启免费投币",
        "note_off": "免费投币已还原",
    },
    {
        "key": "tutorial",
        "title": "跳过教程视频",
        "detail": "对战、游客、新手旅程、离线开局不再播教程。",
        "note_on": "教程视频已跳过",
        "note_off": "教程视频已还原",
    },
    {
        "key": "gameover_return",
        "title": "游戏结束自动返回主菜单兜底",
        "detail": "20 秒未点或 4 秒卡死时强制回 Title。",
        "note_on": "游戏结束已加返回主菜单兜底",
        "note_off": "游戏结束返回主菜单兜底已还原",
    },
)

CATEGORIES = (
    {
        "id": "songs",
        "icon": "♪",
        "title": "选歌与谱面",
        "sub": "难度解锁 · 离线选歌",
        "desc": "解除谱面难度与离线选歌限制",
        "keys": ("clear", "offline", "masterlist"),
    },
    {
        "id": "items",
        "icon": "❖",
        "title": "物品与货币",
        "sub": "音符皮肤 · 道具货币",
        "desc": "解锁全部音符皮肤并锁定道具与货币数量",
        "keys": ("notes", "items", "coins", "gems"),
    },
    {
        "id": "timers",
        "icon": "✧",
        "title": "倒计时控制",
        "sub": "界面与局内秒数停驻",
        "desc": "自定义各界面与局内倒计时停驻秒数",
        "keys": ("song", "mode10", "mode99", "item", "play"),
    },
    {
        "id": "system",
        "icon": "✦",
        "title": "系统与高刷",
        "sub": "高刷解锁 · 触控框体",
        "desc": "高刷帧率解锁、垂直同步、触屏修复、免投币与系统补丁",
        "keys": ("fps", "vsync_off", "fps_display", "fix_touch", "no_io", "free_play", "tutorial", "gameover_return"),
    },
)


# ==============================================================================
# Core Patching & Memory Decryption Logic (100% Untouched)
# ==============================================================================
def find_dll(root: Path) -> Path | None:
    dll = root / DLL_TAIL
    if dll.is_file():
        return dll
    return None


def bak_path(dll: Path) -> Path:
    return dll.parent / (dll.name + ".bak")


def is_encrypted_dll(data: bytes) -> bool:
    if len(data) < 0x100 or data[:2] != b"MZ":
        return True
    return data[12:16] != b"\xff\xff\x00\x00"


class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD),
        ("__alignment1", wt.DWORD),
        ("RegionSize", ctypes.c_uint64),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("__alignment2", wt.DWORD),
    ]


def decrypt_via_game(root: Path, dll_path: Path, expected_size: int) -> bytes:
    exe_path = root / EXE_TAIL
    if not exe_path.is_file():
        raise OSError(t("找不到 {exe}", exe=exe_path))

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 6  # SW_MINIMIZE
    proc = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), startupinfo=si)

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wt.HANDLE
    kernel32.VirtualQueryEx.argtypes = [
        wt.HANDLE,
        ctypes.c_uint64,
        ctypes.POINTER(_MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t
    kernel32.ReadProcessMemory.argtypes = [
        wt.HANDLE,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]

    sig = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    h_proc = None
    try:
        h_proc = kernel32.OpenProcess(0x0010 | 0x0400, False, proc.pid)
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            mbi = _MEMORY_BASIC_INFORMATION()
            addr = 0
            while addr < 0x7FFF0000:
                if not kernel32.VirtualQueryEx(h_proc, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    break
                if mbi.State == 0x1000 and (mbi.Protect & 0xEE) and mbi.RegionSize <= 32 * 1024 * 1024:
                    buf = (ctypes.c_char * mbi.RegionSize)()
                    nread = ctypes.c_size_t()
                    if kernel32.ReadProcessMemory(h_proc, mbi.BaseAddress, buf, mbi.RegionSize, ctypes.byref(nread)):
                        mem = bytes(buf[:nread.value])
                        idx = 0
                        while True:
                            idx = mem.find(sig, idx)
                            if idx == -1:
                                break
                            chunk = mem[idx : idx + expected_size]
                            if len(chunk) == expected_size and b"BSJB" in chunk and b"Assembly-CSharp.dll" in chunk:
                                return chunk
                            idx += 16
                addr = mbi.BaseAddress + mbi.RegionSize
            time.sleep(0.5)
        raise OSError(t("未能在游戏进程内存中找到解密后的 Assembly-CSharp.dll"))
    finally:
        if h_proc:
            kernel32.CloseHandle(h_proc)
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


def run_patcher(args: list[str]) -> str:
    if not PATCHER_EXE.is_file():
        raise OSError(t("找不到 {path}", path=PATCHER_EXE))
    proc = subprocess.run(
        [str(PATCHER_EXE)] + args,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise OSError(proc.stderr.strip() or proc.stdout.strip() or t("TopStar2Patcher 返回 {code}", code=proc.returncode))
    return proc.stdout


def inspect_dll(path: Path) -> dict:
    out = run_patcher(["inspect", str(path)])
    found = {}
    for line in out.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        parts = val.split("|")
        state = parts[0]
        entry = {"state": state}
        if len(parts) > 1:
            try:
                num = float(parts[1])
                entry["seconds"] = int(num) if num == int(num) else num
            except ValueError:
                pass
        found[key] = entry
    return found


def parse_seconds(text: str, low: int, high: int, places: int) -> float | int:
    value = float(text.strip())
    if places == 0 and value != int(value):
        raise ValueError(t("要填整数"))
    number = int(value) if places == 0 else value
    if number < low or number > high:
        raise ValueError(t("要在 {low} 到 {high} 之间", low=low, high=high))
    return number


def format_note(raw_line: str) -> str | None:
    if not raw_line.startswith("NOTE:"):
        return None
    parts = raw_line.split(":")
    key = parts[1]
    action = parts[2]
    val = parts[3] if len(parts) > 3 else ""

    for spec in HOLDS:
        if spec["key"] == key:
            if action == "locked":
                return t("{title} 停在 {seconds} 秒", title=t(spec["title"]), seconds=val)
            return t("{title} 已还原", title=t(spec["title"]))
    if key == "play":
        if action == "locked":
            return t("局内倒计时停在 {seconds} 秒", seconds=val)
        return t("局内倒计时已还原")
    if key == "fps":
        if action == "locked":
            return t("高刷与高帧率已设为 {fps}Hz / {fps}FPS", fps=val)
        return t("高刷与高帧率已还原")
    for spec in FLAGS + OTHER_FLAGS:
        if spec["key"] == key:
            return t(spec["note_on"] if action == "locked" else spec["note_off"])
    return raw_line


def _enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _detect_dpi_scale() -> float:
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi >= 96:
            return dpi / 96.0
    except Exception:
        pass
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        if dpi >= 96:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


class _ScaledCanvas:
    """Transparent proxy that scales logical 96-DPI canvas coordinates to physical HiDPI pixels."""

    def __init__(self, cv: tk.Canvas, scale: float) -> None:
        self._cv = cv
        self._scale = scale

    def _sc(self, v: float) -> int:
        if v == 0:
            return 0
        return max(1, int(round(v * self._scale))) if v > 0 else -max(1, int(round(-v * self._scale)))

    def create_image(self, x: float, y: float, **kw):
        return self._cv.create_image(self._sc(x), self._sc(y), **kw)

    def create_text(self, x: float, y: float, **kw):
        return self._cv.create_text(self._sc(x), self._sc(y), **kw)

    def create_rectangle(self, x1: float, y1: float, x2: float, y2: float, **kw):
        return self._cv.create_rectangle(self._sc(x1), self._sc(y1), self._sc(x2), self._sc(y2), **kw)

    def create_oval(self, x1: float, y1: float, x2: float, y2: float, **kw):
        return self._cv.create_oval(self._sc(x1), self._sc(y1), self._sc(x2), self._sc(y2), **kw)

    def create_window(self, x: float, y: float, **kw):
        if "width" in kw:
            kw["width"] = self._sc(kw["width"])
        if "height" in kw:
            kw["height"] = self._sc(kw["height"])
        return self._cv.create_window(self._sc(x), self._sc(y), **kw)

    def coords(self, tag_or_id, *args):
        if not args:
            return self._cv.coords(tag_or_id)
        return self._cv.coords(tag_or_id, *(self._sc(a) for a in args))

    def __getattr__(self, name: str):
        return getattr(self._cv, name)


def _load_theme_pref() -> str:
    try:
        if PREFS_FILE.is_file():
            data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            if data.get("theme") in ("dark", "light"):
                return data["theme"]
    except Exception:
        pass
    return "dark"


def _save_theme_pref(mode: str) -> None:
    try:
        PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREFS_FILE.write_text(json.dumps({"theme": mode}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# Haute-Couture Dual Theme Specification
# ==============================================================================
_THEMES = {
    "dark": {
        "is_dark": True,
        "base_rgb": (9, 11, 21),
        "blooms": [
            # (rel_x, rel_y, radius_scale, (R, G, B), strength)
            (0.14, 0.12, 0.56, (108, 72, 235), 0.36),
            (0.84, 0.16, 0.48, (56, 88, 210), 0.25),
            (0.55, 0.52, 0.55, (72, 52, 165), 0.18),
            (0.88, 0.90, 0.50, (198, 146, 68), 0.22),
        ],
        "frame_outer": (78, 70, 122, 235),
        "horizon_gold": (246, 214, 142),
        "horizon_iris": (152, 126, 255),
        "card_top_rgba": (26, 31, 54, 218),
        "card_bot_rgba": (16, 20, 38, 232),
        "card_border_a": (236, 198, 122, 150),
        "card_border_b": (124, 106, 242, 115),
        "card_border_c": (52, 62, 104, 95),
        "card_shadow": (2, 4, 10, 145),
        "entry_bg": "#0D1020",
        "entry_fg": "#F7F3EA",
        "entry_caret": "#F0CF86",
        "text_title": "#FAF6EE",
        "text_primary": "#F3EFE6",
        "text_sub": "#B8C0DC",
        "text_muted": "#828CB0",
        "gold_bright": "#F4D690",
        "gold_deep": "#C89B46",
        "iris_bright": "#A89BFF",
        # Interactive surfaces
        "vault_top": (12, 15, 30, 238),
        "vault_bot": (15, 19, 36, 238),
        "vault_bd": (68, 78, 128, 175),
        "vault_focus_bd": (236, 198, 122, 235),
        # Nav cards
        "nav_idle_top": (25, 30, 54, 145),
        "nav_idle_bot": (19, 23, 43, 145),
        "nav_idle_bd": (58, 68, 112, 95),
        "nav_hover_top": (34, 41, 72, 195),
        "nav_hover_bot": (25, 31, 56, 195),
        "nav_hover_bd": (118, 108, 210, 155),
        "nav_act_top": (50, 44, 98, 235),
        "nav_act_bot": (30, 29, 66, 235),
        "nav_act_bd_a": (244, 208, 132, 230),
        "nav_act_bd_b": (132, 110, 250, 200),
        # Feature row capsules
        "row_hero_top": (44, 39, 88, 225),
        "row_hero_bot": (27, 27, 60, 225),
        "row_hero_bd_a": (244, 208, 132, 210),
        "row_hero_bd_b": (134, 110, 250, 185),
        "row_on_top": (29, 35, 64, 198),
        "row_on_bot": (22, 27, 50, 198),
        "row_on_bd": (92, 104, 176, 135),
        "row_off_top": (20, 24, 45, 135),
        "row_off_bot": (17, 21, 39, 135),
        "row_off_bd": (48, 56, 94, 85),
        "row_hover_top": (33, 40, 72, 210),
        "row_hover_bot": (25, 31, 57, 210),
        "row_hover_bd": (138, 126, 225, 165),
        # Buttons & Pills
        "cta_a": (122, 92, 255),
        "cta_b": (82, 64, 218),
        "cta_hover_a": (142, 112, 255),
        "cta_hover_b": (98, 78, 235),
        "cta_rim_a": (252, 224, 156, 255),
        "cta_rim_b": (196, 146, 68, 235),
        "cta_glow": (126, 96, 255, 125),
        "gold_btn_top": (54, 44, 38, 235),
        "gold_btn_bot": (36, 30, 30, 235),
        "gold_btn_hover_top": (72, 58, 46, 245),
        "gold_btn_hover_bot": (48, 39, 36, 245),
        "gold_btn_bd": (228, 188, 112, 205),
        "gold_btn_fg": "#F5D792",
        "sec_btn_top": (34, 40, 70, 220),
        "sec_btn_bot": (24, 29, 53, 220),
        "sec_btn_hover_top": (45, 53, 90, 235),
        "sec_btn_hover_bot": (32, 39, 68, 235),
        "sec_btn_bd": (82, 95, 152, 165),
        "sec_btn_fg": "#EAE6DC",
        # Status badges
        "badge_on_top": (28, 52, 56, 230),
        "badge_on_bot": (21, 39, 45, 230),
        "badge_on_bd": (106, 214, 178, 175),
        "badge_on_fg": "#8AF3CF",
        "badge_orig_bg": (24, 29, 52, 150),
        "badge_orig_bd": (62, 72, 114, 110),
        "badge_orig_fg": "#7D87AA",
        "badge_warn_bg": (68, 28, 42, 225),
        "badge_warn_bd": (225, 96, 128, 185),
        "badge_warn_fg": "#FF9EB5",
        "pip_on": "#6EE7B7",
        # Switch
        "sw_off_top": (28, 34, 60),
        "sw_off_bd": (74, 86, 136),
        "sw_on_a": (128, 96, 255),
        "sw_on_b": (92, 72, 228),
        "sw_knob_rim": (248, 220, 154),
    },
    "light": {
        "is_dark": False,
        "base_rgb": (246, 242, 234),
        "blooms": [
            (0.15, 0.10, 0.58, (255, 236, 196), 0.72),
            (0.85, 0.14, 0.50, (216, 214, 252), 0.62),
            (0.52, 0.54, 0.56, (255, 250, 240), 0.55),
            (0.86, 0.88, 0.52, (238, 214, 178), 0.48),
        ],
        "frame_outer": (214, 198, 168, 245),
        "horizon_gold": (212, 164, 76),
        "horizon_iris": (118, 104, 235),
        "card_top_rgba": (255, 255, 255, 226),
        "card_bot_rgba": (251, 248, 241, 236),
        "card_border_a": (216, 182, 116, 175),
        "card_border_b": (168, 160, 232, 135),
        "card_border_c": (224, 216, 200, 165),
        "card_shadow": (118, 98, 68, 36),
        "entry_bg": "#F3EFE6",
        "entry_fg": "#1E2136",
        "entry_caret": "#9A6E1F",
        "text_title": "#181B2E",
        "text_primary": "#21253B",
        "text_sub": "#4E5470",
        "text_muted": "#7D839C",
        "gold_bright": "#9E6E1B",
        "gold_deep": "#B8862D",
        "iris_bright": "#584CE0",
        # Interactive surfaces
        "vault_top": (243, 239, 230, 245),
        "vault_bot": (246, 243, 236, 245),
        "vault_bd": (216, 206, 186, 210),
        "vault_focus_bd": (188, 142, 58, 245),
        # Nav cards
        "nav_idle_top": (252, 250, 245, 175),
        "nav_idle_bot": (246, 242, 234, 175),
        "nav_idle_bd": (228, 220, 204, 150),
        "nav_hover_top": (255, 255, 255, 235),
        "nav_hover_bot": (248, 245, 254, 235),
        "nav_hover_bd": (182, 174, 238, 195),
        "nav_act_top": (244, 240, 255, 248),
        "nav_act_bot": (235, 230, 252, 248),
        "nav_act_bd_a": (204, 162, 82, 225),
        "nav_act_bd_b": (132, 118, 238, 205),
        # Feature row capsules
        "row_hero_top": (247, 244, 255, 245),
        "row_hero_bot": (240, 235, 252, 245),
        "row_hero_bd_a": (206, 164, 84, 215),
        "row_hero_bd_b": (142, 128, 238, 190),
        "row_on_top": (255, 255, 255, 235),
        "row_on_bot": (249, 247, 254, 235),
        "row_on_bd": (196, 190, 236, 175),
        "row_off_top": (249, 246, 239, 165),
        "row_off_bot": (245, 241, 232, 165),
        "row_off_bd": (228, 221, 206, 145),
        "row_hover_top": (255, 255, 255, 248),
        "row_hover_bot": (247, 244, 253, 248),
        "row_hover_bd": (172, 162, 232, 200),
        # Buttons & Pills
        "cta_a": (98, 80, 238),
        "cta_b": (74, 60, 206),
        "cta_hover_a": (112, 94, 248),
        "cta_hover_b": (86, 70, 220),
        "cta_rim_a": (248, 216, 142, 255),
        "cta_rim_b": (198, 148, 66, 235),
        "cta_glow": (102, 84, 236, 85),
        "gold_btn_top": (254, 248, 232, 248),
        "gold_btn_bot": (247, 235, 204, 248),
        "gold_btn_hover_top": (255, 251, 238, 255),
        "gold_btn_hover_bot": (244, 228, 188, 255),
        "gold_btn_bd": (208, 168, 92, 225),
        "gold_btn_fg": "#8A5E12",
        "sec_btn_top": (255, 254, 251, 242),
        "sec_btn_bot": (244, 239, 229, 242),
        "sec_btn_hover_top": (255, 255, 255, 255),
        "sec_btn_hover_bot": (238, 233, 222, 255),
        "sec_btn_bd": (214, 205, 186, 215),
        "sec_btn_fg": "#2B304A",
        # Status badges
        "badge_on_top": (236, 251, 244, 245),
        "badge_on_bot": (224, 246, 236, 245),
        "badge_on_bd": (136, 212, 180, 210),
        "badge_on_fg": "#126E4D",
        "badge_orig_bg": (244, 240, 232, 185),
        "badge_orig_bd": (220, 213, 198, 165),
        "badge_orig_fg": "#888EA6",
        "badge_warn_bg": (255, 238, 242, 245),
        "badge_warn_bd": (238, 168, 182, 215),
        "badge_warn_fg": "#B82E4B",
        "pip_on": "#10B981",
        # Switch
        "sw_off_top": (224, 218, 206),
        "sw_off_bd": (198, 190, 174),
        "sw_on_a": (104, 84, 240),
        "sw_on_b": (78, 62, 210),
        "sw_knob_rim": (236, 198, 118),
    },
}


# ==============================================================================
# Haute-Couture Graphics Pipeline (2x Supersampled Glass, Gold Bevels & Blooms)
# ==============================================================================
def _pil_to_tk(img: Image.Image | bytes) -> tk.PhotoImage:
    if isinstance(img, (bytes, bytearray)):
        return tk.PhotoImage(data=bytes(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=3)
    return tk.PhotoImage(data=buf.getvalue())


def _encode_png_raw(w: int, h: int, rows: list[bytes]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"".join(b"\x00" + r for r in rows), 6)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _rgba_buf_to_png(w: int, h: int, buf: bytearray) -> bytes:
    stride = w * 4
    rows = [bytes(buf[y * stride : (y + 1) * stride]) for y in range(h)]
    return _encode_png_raw(w, h, rows)


def _lerp_c(c1: tuple[int, ...], c2: tuple[int, ...], t: float) -> tuple[int, int, int, int]:
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    a1 = c1[3] if len(c1) > 3 else 255
    a2 = c2[3] if len(c2) > 3 else 255
    return (
        int(c1[0] + (c2[0] - c1[0]) * t + 0.5),
        int(c1[1] + (c2[1] - c1[1]) * t + 0.5),
        int(c1[2] + (c2[2] - c1[2]) * t + 0.5),
        int(a1 + (a2 - a1) * t + 0.5),
    )


def _put_px_blend(buf: bytearray, w: int, h: int, x: int, y: int, r: int, g: int, b: int, a: int) -> None:
    if a <= 0 or x < 0 or y < 0 or x >= w or y >= h:
        return
    idx = (y * w + x) * 4
    if a >= 255:
        buf[idx] = r
        buf[idx + 1] = g
        buf[idx + 2] = b
        buf[idx + 3] = 255
        return
    da = buf[idx + 3]
    if da == 0:
        buf[idx] = r
        buf[idx + 1] = g
        buf[idx + 2] = b
        buf[idx + 3] = a
        return
    inv = 255 - a
    out_a = a + (da * inv + 127) // 255
    if out_a <= 0:
        return
    buf[idx] = min(255, (r * a + buf[idx] * da * inv // 255) // out_a)
    buf[idx + 1] = min(255, (g * a + buf[idx + 1] * da * inv // 255) // out_a)
    buf[idx + 2] = min(255, (b * a + buf[idx + 2] * da * inv // 255) // out_a)
    buf[idx + 3] = out_a


def _draw_rrect_pure(
    buf: bytearray,
    bw: int,
    bh: int,
    rx: int,
    ry: int,
    rw: int,
    rh: int,
    rad: int,
    top_rgba: tuple[int, int, int, int],
    bot_rgba: tuple[int, int, int, int],
    bd_a: tuple[int, int, int, int] | None = None,
    bd_b: tuple[int, int, int, int] | None = None,
) -> None:
    """Fast pure-Python rounded rectangle with vertical gradient & 1px anti-aliased border."""
    r = max(0, min(rad, rw // 2, rh // 2))
    bd_end = bd_b if bd_b is not None else bd_a
    for ly in range(rh):
        y = ry + ly
        if y < 0 or y >= bh:
            continue
        t_y = ly / max(1, rh - 1)
        fc = _lerp_c(top_rgba, bot_rgba, t_y)
        bc = _lerp_c(bd_a, bd_end, t_y) if bd_a is not None else None
        # Determine horizontal span for this row
        if ly < r:
            dy = r - ly - 0.5
        elif ly >= rh - r:
            dy = ly - (rh - r) + 0.5
        else:
            dy = -1.0

        if dy < 0.0:
            # Middle band: fast row fill + left/right border pixel
            x0 = max(0, rx)
            x1 = min(bw, rx + rw)
            if x1 > x0:
                if fc[3] >= 255:
                    px_bytes = bytes((fc[0], fc[1], fc[2], 255)) * (x1 - x0)
                    st = (y * bw + x0) * 4
                    buf[st : st + len(px_bytes)] = px_bytes
                elif fc[3] > 0:
                    for x in range(x0, x1):
                        _put_px_blend(buf, bw, bh, x, y, fc[0], fc[1], fc[2], fc[3])
                if bc is not None:
                    if ly == 0 or ly == rh - 1:
                        for x in range(x0, x1):
                            _put_px_blend(buf, bw, bh, x, y, bc[0], bc[1], bc[2], bc[3])
                    else:
                        if 0 <= rx < bw:
                            _put_px_blend(buf, bw, bh, rx, y, bc[0], bc[1], bc[2], bc[3])
                        if 0 <= rx + rw - 1 < bw:
                            _put_px_blend(buf, bw, bh, rx + rw - 1, y, bc[0], bc[1], bc[2], bc[3])
        else:
            # Corner band: compute exact x span and anti-aliased corner pixels
            dx_max = math.sqrt(max(0.0, r * r - dy * dy))
            inset = r - dx_max
            ix0 = int(math.floor(inset))
            ix1 = rw - 1 - ix0
            for lx in range(ix0, ix1 + 1):
                x = rx + lx
                if x < 0 or x >= bw:
                    continue
                if lx < r:
                    dx = r - lx - 0.5
                elif lx >= rw - r:
                    dx = lx - (rw - r) + 0.5
                else:
                    dx = 0.0
                if dx > 0.0:
                    dist = math.hypot(dx, dy) - r
                    cov = 1.0 - max(0.0, min(1.0, dist + 0.5))
                    if cov <= 0.0:
                        continue
                    is_edge = dist > -1.35
                else:
                    cov = 1.0
                    is_edge = ly == 0 or ly == rh - 1
                _put_px_blend(buf, bw, bh, x, y, fc[0], fc[1], fc[2], int(fc[3] * cov))
                if bc is not None and is_edge:
                    _put_px_blend(buf, bw, bh, x, y, bc[0], bc[1], bc[2], int(bc[3] * cov))


def _render_glass_capsule_pure(
    w: int,
    h: int,
    radius: int,
    top_rgba: tuple[int, int, int, int],
    bot_rgba: tuple[int, int, int, int],
    bd_a: tuple[int, int, int, int],
    bd_b: tuple[int, int, int, int] | None = None,
    glow_pad: int = 0,
    left_gold_bar: tuple[int, int, int, int] | None = None,
) -> bytes:
    tw = w + glow_pad * 2
    th = h + glow_pad * 2
    buf = bytearray(tw * th * 4)
    _draw_rrect_pure(buf, tw, th, glow_pad, glow_pad, w, h, radius, top_rgba, bot_rgba, bd_a, bd_b)
    if left_gold_bar is not None:
        bm = int(h * 0.22)
        _draw_rrect_pure(
            buf,
            tw,
            th,
            glow_pad + 2,
            glow_pad + bm,
            3,
            max(4, h - bm * 2),
            1,
            left_gold_bar,
            left_gold_bar,
        )
    return _rgba_buf_to_png(tw, th, buf)


def _render_royal_crest_pure(size: int, th: dict) -> bytes:
    buf = bytearray(size * size * 4)
    pad = max(1, int(size * 0.08))
    rr = max(2, int(size * 0.28))
    _draw_rrect_pure(
        buf, size, size, pad, pad, size - pad * 2, size - pad * 2, rr,
        (254, 232, 168, 255), (178, 128, 48, 255),
    )
    in_p = pad + max(2, int(size * 0.06))
    in_r = max(2, rr - 2)
    _draw_rrect_pure(
        buf, size, size, in_p, in_p, size - in_p * 2, size - in_p * 2, in_r,
        (136, 104, 255, 255), (42, 32, 128, 255),
    )
    return _rgba_buf_to_png(size, size, buf)


def _render_folder_icon_pure(size: int, gold_rgb: tuple[int, int, int]) -> bytes:
    buf = bytearray(size * size * 4)
    r, g, b = gold_rgb
    _draw_rrect_pure(
        buf, size, size, int(size * 0.10), int(size * 0.18),
        max(3, int(size * 0.38)), max(3, int(size * 0.24)), max(1, int(size * 0.08)),
        (r, g, b, 210), (r, g, b, 210),
    )
    _draw_rrect_pure(
        buf, size, size, int(size * 0.10), int(size * 0.30),
        max(4, int(size * 0.80)), max(4, int(size * 0.52)), max(1, int(size * 0.10)),
        (min(255, r + 18), min(255, g + 16), min(255, b + 12), 235), (r, g, b, 200),
        (r, g, b, 245),
    )
    return _rgba_buf_to_png(size, size, buf)


def _render_switch_pure(w: int, h: int, progress: float, th: dict, hover: bool) -> bytes:
    pad = 4
    tw, th_px = w + pad * 2, h + pad * 2
    buf = bytearray(tw * th_px * 4)
    off_c = th["sw_off_top"]
    on_a = th["sw_on_a"]
    on_b = th["sw_on_b"]
    c1 = _lerp_c(off_c, on_a, progress)
    c2 = _lerp_c(off_c, on_b, progress)
    if hover:
        c1 = (min(255, c1[0] + 12), min(255, c1[1] + 12), min(255, c1[2] + 12), 255)
        c2 = (min(255, c2[0] + 12), min(255, c2[1] + 12), min(255, c2[2] + 12), 255)
    bd_c = _lerp_c(th["sw_off_bd"] + (165,), th["sw_knob_rim"] + (230,), progress)
    _draw_rrect_pure(buf, tw, th_px, pad, pad, w, h, h // 2, c1, c2, bd_c)

    kr = max(3.0, h * 0.5 - 3.2)
    kx = pad + h * 0.5 + (w - h) * progress
    ky = pad + h * 0.5
    rim = th["sw_knob_rim"]
    y0 = max(0, int(ky - kr - 1))
    y1 = min(th_px, int(ky + kr + 2))
    x0 = max(0, int(kx - kr - 1))
    x1 = min(tw, int(kx + kr + 2))
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = math.hypot(x - kx, y - ky) - kr
            cov = 1.0 - max(0.0, min(1.0, d + 0.5))
            if cov <= 0.0:
                continue
            if d > -1.1:
                _put_px_blend(buf, tw, th_px, x, y, rim[0], rim[1], rim[2], int(220 * cov))
            else:
                _put_px_blend(buf, tw, th_px, x, y, 255, 253, 248, int(255 * cov))
    return _rgba_buf_to_png(tw, th_px, buf)


def _render_scene_backdrop_pure(w: int, h: int, th: dict, cards: list[tuple[int, int, int, int, int]]) -> bytes:
    buf = bytearray(w * h * 4)
    br, bg, bb = th["base_rgb"]
    b_top = (br, bg, bb, 255)
    if th["is_dark"]:
        b_bot = (min(255, br + 12), min(255, bg + 8), min(255, bb + 24), 255)
    else:
        b_bot = (max(0, br - 10), max(0, bg - 10), max(0, bb - 4), 255)
    for y in range(h):
        rc = _lerp_c(b_top, b_bot, y / max(1, h - 1))
        row_b = bytes((rc[0], rc[1], rc[2], 255)) * w
        buf[y * w * 4 : (y + 1) * w * 4] = row_b

    for cx, cy, cw, ch_box, cr in cards:
        _draw_rrect_pure(
            buf, w, h, cx, cy, cw, ch_box, cr,
            th["card_top_rgba"], th["card_bot_rgba"],
            th["card_border_a"], th["card_border_b"],
        )

    # Outer frame border
    fr, fg, fb, fa = th["frame_outer"]
    for x in range(w):
        _put_px_blend(buf, w, h, x, 0, fr, fg, fb, fa)
        _put_px_blend(buf, w, h, x, h - 1, fr, fg, fb, fa)
    for y in range(h):
        _put_px_blend(buf, w, h, 0, y, fr, fg, fb, fa)
        _put_px_blend(buf, w, h, w - 1, y, fr, fg, fb, fa)
    return _rgba_buf_to_png(w, h, buf)


def _make_diagonal_gradient(
    w: int,
    h: int,
    c_tl: tuple[int, int, int, int],
    c_br: tuple[int, int, int, int],
    c_mid: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    t_mat = np.clip(y * 0.62 + x * 0.38, 0.0, 1.0)
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    if c_mid is None:
        for ch in range(4):
            arr[:, :, ch] = np.clip(c_tl[ch] + (c_br[ch] - c_tl[ch]) * t_mat + 0.5, 0, 255).astype(np.uint8)
    else:
        low = np.clip(t_mat * 2.0, 0.0, 1.0)
        high = np.clip((t_mat - 0.5) * 2.0, 0.0, 1.0)
        for ch in range(4):
            v = np.where(
                t_mat < 0.5,
                c_tl[ch] + (c_mid[ch] - c_tl[ch]) * low,
                c_mid[ch] + (c_br[ch] - c_mid[ch]) * high,
            )
            arr[:, :, ch] = np.clip(v + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _render_glass_capsule(
    w: int,
    h: int,
    radius: int,
    top_rgba: tuple[int, int, int, int],
    bot_rgba: tuple[int, int, int, int],
    bd_a: tuple[int, int, int, int],
    bd_b: tuple[int, int, int, int] | None = None,
    glow_rgba: tuple[int, int, int, int] | None = None,
    glow_pad: int = 0,
    left_gold_bar: tuple[int, int, int, int] | None = None,
    top_shine: bool = True,
) -> Image.Image | bytes:
    """2x supersampled luxury capsule with diagonal metallic border & optional outer aura."""
    if not _HAS_PIL:
        return _render_glass_capsule_pure(
            w, h, radius, top_rgba, bot_rgba, bd_a, bd_b, glow_pad, left_gold_bar
        )
    ss = 2
    total_w = w + glow_pad * 2
    total_h = h + glow_pad * 2
    sw, sh = total_w * ss, total_h * ss
    px = glow_pad * ss
    py = glow_pad * ss
    iw, ih = w * ss, h * ss
    rr = radius * ss

    out = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))

    if glow_rgba is not None and glow_pad > 0 and glow_rgba[3] > 0:
        glow_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        gd.rounded_rectangle([px, py + ss, px + iw - 1, py + ih + ss - 1], radius=rr, fill=glow_rgba)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=max(2, glow_pad * ss * 0.48)))
        out = Image.alpha_composite(out, glow_layer)

    # Interior fill
    mask = Image.new("L", (iw, ih), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=rr, fill=255)
    fill_grad = _make_diagonal_gradient(iw, ih, top_rgba, bot_rgba)
    body = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    body.paste(fill_grad, (0, 0), mask)

    # Optional glowing left champagne-gold light blade
    if left_gold_bar is not None:
        bar_layer = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
        bd_draw = ImageDraw.Draw(bar_layer)
        bar_m = int(ih * 0.22)
        bd_draw.rounded_rectangle([2, bar_m, 2 + 3 * ss, ih - bar_m], radius=2 * ss, fill=left_gold_bar)
        bar_glow = bar_layer.filter(ImageFilter.GaussianBlur(radius=3 * ss))
        body = Image.alpha_composite(body, bar_glow)
        body = Image.alpha_composite(body, bar_layer)

    # Gradient metallic border (stroke mask)
    bd_end = bd_b if bd_b is not None else bd_a
    stroke_mask = Image.new("L", (iw, ih), 0)
    sd = ImageDraw.Draw(stroke_mask)
    sd.rounded_rectangle([0, 0, iw - 1, ih - 1], radius=rr, outline=255, width=max(2, int(1.35 * ss)))
    border_grad = _make_diagonal_gradient(iw, ih, bd_a, bd_end)
    border_layer = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    border_layer.paste(border_grad, (0, 0), stroke_mask)
    body = Image.alpha_composite(body, border_layer)

    # Top crystalline specular catchlight
    if top_shine and iw > rr * 2 + 12:
        shine = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
        xs = np.linspace(-1.0, 1.0, iw - rr * 2, dtype=np.float32)
        falloff = np.clip(1.0 - xs * xs, 0.0, 1.0) ** 1.6
        row_arr = np.zeros((2, iw - rr * 2, 4), dtype=np.uint8)
        row_arr[:, :, :3] = 255
        row_arr[0, :, 3] = (falloff * 95).astype(np.uint8)
        row_arr[1, :, 3] = (falloff * 28).astype(np.uint8)
        shine.paste(Image.fromarray(row_arr, "RGBA"), (rr, ss))
        # Clip shine inside mask
        clipped_shine = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
        clipped_shine.paste(shine, (0, 0), mask)
        body = Image.alpha_composite(body, clipped_shine)

    out.alpha_composite(body, (px, py))
    return out.resize((total_w, total_h), Image.Resampling.LANCZOS)


def _render_royal_crest(size: int, th: dict) -> Image.Image | bytes:
    """Renders a bespoke faceted TS2 Royal Amethyst & 18K Champagne Gold medallion."""
    if not _HAS_PIL:
        return _render_royal_crest_pure(size, th)
    ss = 4
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(size * 0.08 * ss)
    rr = int(size * 0.28 * ss)

    # Soft ambient aura
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        [pad, pad + ss, s - pad - 1, s - pad - 1],
        radius=rr,
        fill=(124, 96, 255, 115 if th["is_dark"] else 75),
    )
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(radius=size * 0.22)))

    # Outer 18K Champagne Gold bezel
    bezel_mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(bezel_mask).rounded_rectangle([pad, pad, s - pad - 1, s - pad - 1], radius=rr, fill=255)
    gold_grad = _make_diagonal_gradient(
        s, s, (254, 232, 168, 255), (178, 128, 48, 255), (232, 190, 102, 255)
    )
    img.paste(gold_grad, (0, 0), bezel_mask)

    # Inner Royal Amethyst-Sapphire enamel dome
    in_p = pad + max(3, int(1.8 * ss))
    in_r = max(4, rr - int(1.6 * ss))
    dome_mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(dome_mask).rounded_rectangle([in_p, in_p, s - in_p - 1, s - in_p - 1], radius=in_r, fill=255)
    enamel = _make_diagonal_gradient(
        s, s, (136, 104, 255, 255), (42, 32, 128, 255), (86, 64, 208, 255)
    )
    img.paste(enamel, (0, 0), dome_mask)

    # Subtle upper-left crystal lens sheen + inner diamond star accent
    sheen = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.pieslice([in_p - s // 4, in_p - s // 3, s - in_p + s // 5, in_p + int(s * 0.42)], 0, 180, fill=(255, 255, 255, 48))
    # Tiny 4-point gold star at top-right inside dome
    cx, cy = s - in_p - int(s * 0.17), in_p + int(s * 0.17)
    sr = max(3, int(s * 0.065))
    pts = [
        (cx, cy - sr), (cx + sr * 0.28, cy - sr * 0.28),
        (cx + sr, cy), (cx + sr * 0.28, cy + sr * 0.28),
        (cx, cy + sr), (cx - sr * 0.28, cy + sr * 0.28),
        (cx - sr, cy), (cx - sr * 0.28, cy - sr * 0.28),
    ]
    sd.polygon(pts, fill=(255, 234, 176, 235))
    clipped = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    clipped.paste(sheen, (0, 0), dome_mask)
    img = Image.alpha_composite(img, clipped)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _render_folder_icon(size: int, gold_rgb: tuple[int, int, int]) -> Image.Image | bytes:
    if not _HAS_PIL:
        return _render_folder_icon_pure(size, gold_rgb)
    ss = 4
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = gold_rgb
    # Back tab
    d.rounded_rectangle([int(s * 0.10), int(s * 0.18), int(s * 0.48), int(s * 0.42)], radius=int(s * 0.08), fill=(r, g, b, 210))
    d.rounded_rectangle([int(s * 0.10), int(s * 0.28), int(s * 0.90), int(s * 0.82)], radius=int(s * 0.10), fill=(r, g, b, 155), outline=(r, g, b, 245), width=max(2, ss // 2))
    # Front flap highlight
    d.rounded_rectangle([int(s * 0.10), int(s * 0.40), int(s * 0.90), int(s * 0.82)], radius=int(s * 0.10), fill=(min(255, r + 18), min(255, g + 16), min(255, b + 12), 235))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _render_switch_pil(w: int, h: int, progress: float, th: dict, hover: bool) -> Image.Image | bytes:
    if not _HAS_PIL:
        return _render_switch_pure(w, h, progress, th, hover)
    ss = 3
    pad = 4
    tw, th_px = (w + pad * 2) * ss, (h + pad * 2) * ss
    px, py = pad * ss, pad * ss
    iw, ih = w * ss, h * ss
    rr = ih // 2

    out = Image.new("RGBA", (tw, th_px), (0, 0, 0, 0))
    if progress > 0.05:
        glow = Image.new("RGBA", (tw, th_px), (0, 0, 0, 0))
        a = int((115 if hover else 85) * progress)
        ImageDraw.Draw(glow).rounded_rectangle(
            [px, py + ss // 2, px + iw - 1, py + ih - 1],
            radius=rr,
            fill=(th["sw_on_a"][0], th["sw_on_a"][1], th["sw_on_a"][2], a),
        )
        out = Image.alpha_composite(out, glow.filter(ImageFilter.GaussianBlur(radius=3.5 * ss)))

    track_mask = Image.new("L", (iw, ih), 0)
    ImageDraw.Draw(track_mask).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=rr, fill=255)

    off_c = th["sw_off_top"]
    on_a = th["sw_on_a"]
    on_b = th["sw_on_b"]
    c1 = tuple(int(off_c[i] * (1.0 - progress) + on_a[i] * progress) for i in range(3)) + (255,)
    c2 = tuple(int(off_c[i] * (1.0 - progress) + on_b[i] * progress) for i in range(3)) + (255,)
    if hover:
        c1 = tuple(min(255, v + 12) for v in c1[:3]) + (255,)
        c2 = tuple(min(255, v + 12) for v in c2[:3]) + (255,)

    track_body = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    track_body.paste(_make_diagonal_gradient(iw, ih, c1, c2), (0, 0), track_mask)

    bd_rgb = th["sw_off_bd"]
    rim_rgb = th["sw_knob_rim"]
    bd_c = tuple(int(bd_rgb[i] * (1.0 - progress) + rim_rgb[i] * progress) for i in range(3)) + (int(165 + 65 * progress),)
    ImageDraw.Draw(track_body).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=rr, outline=bd_c, width=max(2, int(1.2 * ss)))
    out.alpha_composite(track_body, (px, py))

    # Pearl-champagne 3D knob
    kr = int((ih * 0.5) - 3.2 * ss)
    kx_min = px + int(ih * 0.5)
    kx_max = px + iw - int(ih * 0.5)
    kx = int(kx_min + (kx_max - kx_min) * progress)
    ky = py + ih // 2

    knob_sh = Image.new("RGBA", (tw, th_px), (0, 0, 0, 0))
    ImageDraw.Draw(knob_sh).ellipse([kx - kr, ky - kr + ss, kx + kr, ky + kr + ss], fill=(0, 0, 0, 80))
    out = Image.alpha_composite(out, knob_sh.filter(ImageFilter.GaussianBlur(radius=1.5 * ss)))

    kd = ImageDraw.Draw(out)
    kd.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=(255, 253, 248, 255), outline=rim_rgb + (int(120 + 110 * progress),), width=max(1, ss // 2))
    return out.resize((w + pad * 2, h + pad * 2), Image.Resampling.LANCZOS)


def _render_scene_backdrop(w: int, h: int, th: dict, cards: list[tuple[int, int, int, int, int]]) -> Image.Image | bytes:
    """Renders the full-window multi-aurora light field + frosted glass cards + gold horizon flare."""
    if not _HAS_PIL:
        return _render_scene_backdrop_pure(w, h, th, cards)
    # Compute smooth aurora at 1/4 resolution for silky organic light diffusion in <4ms
    gw, gh = max(64, w // 4), max(64, h // 4)
    yy = np.linspace(0.0, 1.0, gh, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, gw, dtype=np.float32)[None, :]
    aspect = float(w) / max(1.0, float(h))

    rgb = np.zeros((gh, gw, 3), dtype=np.float32)
    rgb[:, :, 0] = th["base_rgb"][0]
    rgb[:, :, 1] = th["base_rgb"][1]
    rgb[:, :, 2] = th["base_rgb"][2]

    for bx, by, brad, bcol, bstr in th["blooms"]:
        dx = (xx - bx) * aspect
        dy = yy - by
        d2 = (dx * dx + dy * dy) / max(0.01, brad * brad)
        wgt = np.exp(-d2 * 2.2) * bstr
        if th["is_dark"]:
            for ch in range(3):
                rgb[:, :, ch] += bcol[ch] * wgt
        else:
            for ch in range(3):
                rgb[:, :, ch] = rgb[:, :, ch] * (1.0 - wgt) + bcol[ch] * wgt

    bg_small = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8), "RGB")
    scene = bg_small.resize((w, h), Image.Resampling.BICUBIC).convert("RGBA")

    # Subtle custom titlebar crown tint & champagne hairline at y=44
    crown = Image.new("RGBA", (w, 45), (255, 255, 255, 6) if th["is_dark"] else (255, 255, 255, 95))
    scene.alpha_composite(crown, (0, 0))
    hline = Image.new("RGBA", (w - 36, 1), (0, 0, 0, 0))
    xs = np.linspace(-1.0, 1.0, w - 36, dtype=np.float32)
    hl_alpha = ((1.0 - xs * xs) ** 1.4 * (68 if th["is_dark"] else 88)).astype(np.uint8)
    hl_arr = np.zeros((1, w - 36, 4), dtype=np.uint8)
    hl_arr[0, :, :3] = th["horizon_gold"]
    hl_arr[0, :, 3] = hl_alpha
    hline = Image.fromarray(hl_arr, "RGBA")
    scene.alpha_composite(hline, (18, 44))

    # Composite 4 Frosted Glass Cards with soft drop shadows & metallic gold-iris rims
    sh_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh_layer)
    for cx, cy, cw, ch_box, cr in cards:
        sd.rounded_rectangle([cx + 1, cy + 5, cx + cw - 2, cy + ch_box + 4], radius=cr, fill=th["card_shadow"])
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=11))
    scene = Image.alpha_composite(scene, sh_layer)

    for cx, cy, cw, ch_box, cr in cards:
        card_img = _render_glass_capsule(
            cw,
            ch_box,
            cr,
            th["card_top_rgba"],
            th["card_bot_rgba"],
            th["card_border_a"],
            th["card_border_b"],
            top_shine=True,
        )
        scene.alpha_composite(card_img, (cx, cy))

    # Right panel subtle decorative header light-fade line
    if len(cards) >= 3:
        rx, ry, rw, _, _ = cards[2]
        lw = rw - 52
        l_arr = np.zeros((1, lw, 4), dtype=np.uint8)
        t_x = np.linspace(0.0, 1.0, lw, dtype=np.float32)
        for ch_i in range(3):
            l_arr[0, :, ch_i] = (
                th["horizon_gold"][ch_i] * (1.0 - t_x) + th["horizon_iris"][ch_i] * t_x
            ).astype(np.uint8)
        l_arr[0, :, 3] = ((1.0 - t_x) ** 1.3 * (120 if th["is_dark"] else 135)).astype(np.uint8)
        scene.alpha_composite(Image.fromarray(l_arr, "RGBA"), (rx + 26, ry + 52))

    # Left sidebar bottom divider before Quick Actions
    if len(cards) >= 2:
        sx, sy, sw_b, sh_b, _ = cards[1]
        qlw = sw_b - 36
        q_arr = np.zeros((1, qlw, 4), dtype=np.uint8)
        qx = np.linspace(-1.0, 1.0, qlw, dtype=np.float32)
        q_arr[0, :, :3] = th["horizon_gold"]
        q_arr[0, :, 3] = ((1.0 - qx * qx) * (75 if th["is_dark"] else 95)).astype(np.uint8)
        scene.alpha_composite(Image.fromarray(q_arr, "RGBA"), (sx + 18, sy + sh_b - 86))

    # Outer Haute Window Bevel + Top-Center Horizon Specular Flare
    od = ImageDraw.Draw(scene)
    od.rectangle([0, 0, w - 1, h - 1], outline=th["frame_outer"], width=1)
    flare_w = min(w - 80, 620)
    fx = (w - flare_w) // 2
    f_arr = np.zeros((2, flare_w, 4), dtype=np.uint8)
    ft = np.linspace(-1.0, 1.0, flare_w, dtype=np.float32)
    env = np.clip(1.0 - ft * ft, 0.0, 1.0) ** 2.2
    for ch_i in range(3):
        f_arr[:, :, ch_i] = int(th["horizon_gold"][ch_i] * 0.7 + 255 * 0.3)
    f_arr[0, :, 3] = (env * (225 if th["is_dark"] else 190)).astype(np.uint8)
    f_arr[1, :, 3] = (env * 65).astype(np.uint8)
    scene.alpha_composite(Image.fromarray(f_arr, "RGBA"), (fx, 0))

    return scene


# ==============================================================================
# Win32 Frameless Taskbar & File-Drop Integration
# ==============================================================================
_WNDPROC_TYPE = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
_WM_DROPFILES = 0x0233


class App(tk.Tk):
    BASE_W = 1080
    BASE_H = 788

    def __init__(self):
        _enable_dpi_awareness()
        super().__init__()
        self.overrideredirect(True)
        self.theme_mode = _load_theme_pref()
        self.cur_w = self.BASE_W
        self.cur_h = self.BASE_H
        self._is_maximized = False
        self._restore_box: tuple[int, int, int, int] | None = None
        self._drag_origin: tuple[int, int, int, int] | None = None

        self.path = tk.StringVar(value="")
        self.file_path = tk.StringVar(value="")
        self.rows: dict[str, dict] = {}
        self.active_tab = "songs"
        self._img_cache: dict[tuple, tk.PhotoImage] = {}
        self._live_refs: list[tk.PhotoImage] = []
        self._last_path: Path | None = None
        self._last_found: dict | None = None
        self._old_wndproc = None
        self._wndproc_ref = None
        self._hwnd: int = 0

        self._init_state_models()
        self._setup_icon()
        self._fit_initial_geometry()
        self._build_canvas_ui()
        self._setup_win32_frameless_and_drop()

    @property
    def th(self) -> dict:
        return _THEMES[self.theme_mode]

    def _s(self, v: float) -> int:
        if v == 0:
            return 0
        return max(1, int(round(v * self._ui_scale))) if v > 0 else -max(1, int(round(-v * self._ui_scale)))

    def _font(self, size: int = 9, weight: str = "normal") -> tuple[str, int, str]:
        family = "Microsoft YaHei UI" if i18n.is_chinese() else "Segoe UI"
        px = -max(9, int(round(size * 96 / 72 * self._ui_scale)))
        return (family, px, weight)

    def _mono(self, size: int = 9, weight: str = "bold") -> tuple[str, int, str]:
        px = -max(9, int(round(size * 96 / 72 * self._ui_scale)))
        return ("Consolas", px, weight)

    def _init_state_models(self) -> None:
        all_flags = list(FLAGS) + list(OTHER_FLAGS)
        for spec in all_flags:
            self.rows[spec["key"]] = {
                "lock": tk.BooleanVar(value=False),
                "seconds": None,
                "badge_kind": "idle",
                "badge_text": "",
                "anim_step": 0,
                "anim_job": None,
            }
        for spec in list(HOLDS) + [PLAY_SPEC]:
            self.rows[spec["key"]] = {
                "lock": tk.BooleanVar(value=False),
                "seconds": tk.StringVar(value=str(spec["default"])),
                "spec": spec,
                "badge_kind": "idle",
                "badge_text": "",
                "anim_step": 0,
                "anim_job": None,
            }
        self.rows["fps"] = {
            "lock": tk.BooleanVar(value=False),
            "seconds": tk.StringVar(value="120"),
            "badge_kind": "idle",
            "badge_text": "",
            "anim_step": 0,
            "anim_job": None,
        }

    def _setup_icon(self) -> None:
        try:
            crest_64 = _pil_to_tk(_render_royal_crest(64, self.th))
            crest_32 = _pil_to_tk(_render_royal_crest(32, self.th))
            self._icon_refs = (crest_64, crest_32)
            self.iconphoto(True, crest_64, crest_32)
        except Exception:
            pass

    def _work_area(self) -> tuple[int, int, int, int]:
        rect = wt.RECT()
        try:
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:
            pass
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _fit_initial_geometry(self) -> None:
        wx, wy, ww, wh = self._work_area()
        dpi_scale = _detect_dpi_scale()
        self._ui_scale = max(1.0, min(dpi_scale, (ww - 24) / self.BASE_W, (wh - 24) / self.BASE_H))
        self.cur_w = min(ww - 20, max(980, self._s(self.BASE_W)))
        self.cur_h = min(wh - 20, max(720, self._s(self.BASE_H)))
        x = wx + max(0, (ww - self.cur_w) // 2)
        y = wy + max(0, (wh - self.cur_h) // 2)
        self.geometry(f"{self.cur_w}x{self.cur_h}+{x}+{y}")

    def _setup_win32_frameless_and_drop(self) -> None:
        try:
            self.update_idletasks()
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_void_p]
            user32.SetWindowLongPtrW.restype = ctypes.c_void_p
            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
            user32.CallWindowProcW.restype = ctypes.c_ssize_t
            shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wt.UINT, wt.LPWSTR, wt.UINT]
            shell32.DragQueryFileW.restype = wt.UINT
            shell32.DragFinish.argtypes = [ctypes.c_void_p]

            hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            self._hwnd = hwnd

            # Ensure Taskbar icon presence & native minimize support
            style = user32.GetWindowLongW(hwnd, -16)
            user32.SetWindowLongW(hwnd, -16, style | 0x00020000 | 0x00080000)
            ex = user32.GetWindowLongW(hwnd, -20)
            user32.SetWindowLongW(hwnd, -20, (ex & ~0x00000080) | 0x00040000)

            self.withdraw()
            self.deiconify()

            shell32.DragAcceptFiles(hwnd, True)

            def _wndproc(h, msg, wp, lp):
                if msg == _WM_DROPFILES:
                    buf = ctypes.create_unicode_buffer(1024)
                    if shell32.DragQueryFileW(wp, 0, buf, 1024) > 0:
                        dropped = Path(buf.value)
                        shell32.DragFinish(wp)
                        self.after(10, lambda p=dropped: self._handle_dropped_path(p))
                        return 0
                    shell32.DragFinish(wp)
                return user32.CallWindowProcW(self._old_wndproc, h, msg, wp, lp)

            self._wndproc_ref = _WNDPROC_TYPE(_wndproc)
            self._old_wndproc = user32.SetWindowLongPtrW(
                hwnd, -4, ctypes.cast(self._wndproc_ref, ctypes.c_void_p).value
            )
        except Exception:
            pass

    def _minimize_window(self) -> None:
        if self._hwnd:
            ctypes.windll.user32.ShowWindow(self._hwnd, 6)  # SW_MINIMIZE

    def _request_close(self) -> None:
        self.after(10, self.destroy)

    def destroy(self) -> None:
        for row in self.rows.values():
            job = row.get("anim_job")
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                row["anim_job"] = None
        if self._hwnd and self._old_wndproc:
            try:
                user32 = ctypes.windll.user32
                user32.SetWindowLongPtrW(self._hwnd, -4, self._old_wndproc)
            except Exception:
                pass
            self._old_wndproc = None
            self._wndproc_ref = None
        self._live_refs.clear()
        self._img_cache.clear()
        self._icon_refs = None
        try:
            self.quit()
        except Exception:
            pass
        super().destroy()

    def _toggle_maximize(self) -> None:
        wx, wy, ww, wh = self._work_area()
        if not self._is_maximized:
            self._restore_box = (self.winfo_x(), self.winfo_y(), self.cur_w, self.cur_h)
            self._is_maximized = True
            self.cur_w, self.cur_h = ww, wh
            self.geometry(f"{ww}x{wh}+{wx}+{wy}")
        else:
            self._is_maximized = False
            rx, ry, rw, rh = self._restore_box or (wx + (ww - self.BASE_W) // 2, wy + (wh - self.BASE_H) // 2, self.BASE_W, self.BASE_H)
            self.cur_w, self.cur_h = rw, rh
            self.geometry(f"{rw}x{rh}+{rx}+{ry}")
        self._build_canvas_ui()

    def _handle_dropped_path(self, dropped: Path) -> None:
        cand = dropped if dropped.is_dir() else dropped.parent
        for check in [cand] + list(cand.parents)[:4]:
            if find_dll(check) is not None:
                self.path.set(str(check))
                self.read_status()
                return
        self.path.set(str(cand))
        self.read_status()

    # ==========================================================================
    # Cached Supersampled Asset Helpers
    # ==========================================================================
    def _cap_img(self, key_extra: tuple, **kwargs) -> tk.PhotoImage:
        sk = round(self._ui_scale, 3)
        k = ("cap", self.theme_mode, sk) + key_extra
        img = self._img_cache.get(k)
        if img is None:
            kw = dict(kwargs)
            for dim in ("w", "h", "radius"):
                if dim in kw:
                    kw[dim] = self._s(kw[dim])
            if kw.get("glow_pad", 0) > 0:
                kw["glow_pad"] = self._s(kw["glow_pad"])
            img = _pil_to_tk(_render_glass_capsule(**kw))
            self._img_cache[k] = img
        return img

    def _sw_img(self, step: int, hover: bool) -> tk.PhotoImage:
        sk = round(self._ui_scale, 3)
        k = ("sw", self.theme_mode, sk, step, hover)
        img = self._img_cache.get(k)
        if img is None:
            img = _pil_to_tk(_render_switch_pil(self._s(46), self._s(25), step / 4.0, self.th, hover))
            self._img_cache[k] = img
        return img

    def _crest_img(self, size: int) -> tk.PhotoImage:
        sk = round(self._ui_scale, 3)
        k = ("crest", self.theme_mode, sk, size)
        img = self._img_cache.get(k)
        if img is None:
            img = _pil_to_tk(_render_royal_crest(self._s(size), self.th))
            self._img_cache[k] = img
        return img

    def _folder_img(self, size: int) -> tk.PhotoImage:
        sk = round(self._ui_scale, 3)
        k = ("folder", self.theme_mode, sk, size)
        img = self._img_cache.get(k)
        if img is None:
            rgb = (244, 214, 144) if self.th["is_dark"] else (188, 138, 48)
            img = _pil_to_tk(_render_folder_icon(self._s(size), rgb))
            self._img_cache[k] = img
        return img

    # ==========================================================================
    # Unified Haute-Couture Canvas Builder
    # ==========================================================================
    def _build_canvas_ui(self) -> None:
        th = self.th
        self.title(t("TopStar2修改器"))
        for child in self.winfo_children():
            child.destroy()
        self._live_refs.clear()

        W, H = self.cur_w, self.cur_h
        raw_cv = tk.Canvas(self, width=W, height=H, highlightthickness=0, bd=0, bg=th["entry_bg"])
        raw_cv.place(x=0, y=0, width=W, height=H)
        cv = _ScaledCanvas(raw_cv, self._ui_scale) if abs(self._ui_scale - 1.0) > 1e-3 else raw_cv
        self.cv = cv

        LW = max(980, int(round(W / self._ui_scale)))
        LH = max(720, int(round(H / self._ui_scale)))

        # Card geometry definitions (in logical 96-DPI coordinates)
        hero_box = (18, 54, LW - 36, 144, 18)
        side_box = (18, 210, 260, LH - 292, 18)
        main_box = (290, 210, LW - 308, LH - 292, 18)
        foot_box = (18, LH - 70, LW - 36, 54, 15)
        self._layout_boxes = (hero_box, side_box, main_box, foot_box)
        scaled_boxes = [tuple(self._s(v) for v in b) for b in self._layout_boxes]

        # 1. Full-scene aurora & frosted glass backdrop
        scene_key = ("scene", self.theme_mode, W, H)
        scene_tk = self._img_cache.get(scene_key)
        if scene_tk is None:
            scene_tk = _pil_to_tk(_render_scene_backdrop(W, H, th, scaled_boxes))
            self._img_cache[scene_key] = scene_tk
        raw_cv.create_image(0, 0, image=scene_tk, anchor="nw")

        # 2. Custom Frameless Titlebar (y = 0..44)
        self._build_titlebar(cv, LW)

        # 3. Hero Console Card
        self._build_hero_card(cv, hero_box)

        # 4. Left Boutique Navigation Sidebar
        self._build_sidebar(cv, side_box)

        # 5. Bottom Signature Action Bar
        self._build_footer(cv, foot_box)

        # 6. Right Feature Gallery (Active Category)
        self._render_active_page()
        self._refresh_summary_and_counts()

    def _canvas_btn(
        self,
        cv: tk.Canvas,
        cx: int,
        cy: int,
        w: int,
        h: int,
        text: str,
        command,
        kind: str = "secondary",
        font_size: int = 9,
        radius: int = 10,
        tag_prefix: str = "btn",
    ) -> tuple[int, int]:
        th = self.th
        if kind == "primary":
            pad = 6
            img_n = self._cap_img(
                ("cta_n", w, h),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["cta_a"] + (255,),
                bot_rgba=th["cta_b"] + (255,),
                bd_a=th["cta_rim_a"],
                bd_b=th["cta_rim_b"],
                glow_rgba=th["cta_glow"],
                glow_pad=pad,
            )
            img_h = self._cap_img(
                ("cta_h", w, h),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["cta_hover_a"] + (255,),
                bot_rgba=th["cta_hover_b"] + (255,),
                bd_a=(255, 240, 186, 255),
                bd_b=th["cta_rim_a"],
                glow_rgba=th["cta_glow"][:3] + (min(210, th["cta_glow"][3] + 55),),
                glow_pad=pad,
            )
            fg = "#FFFFFF"
            weight = "bold"
        elif kind == "gold":
            img_n = self._cap_img(
                ("gold_n", w, h, radius),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["gold_btn_top"],
                bot_rgba=th["gold_btn_bot"],
                bd_a=th["gold_btn_bd"],
                bd_b=th["card_border_b"],
            )
            img_h = self._cap_img(
                ("gold_h", w, h, radius),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["gold_btn_hover_top"],
                bot_rgba=th["gold_btn_hover_bot"],
                bd_a=(248, 214, 140, 245),
                bd_b=th["gold_btn_bd"],
            )
            fg = th["gold_btn_fg"]
            weight = "bold"
        else:
            img_n = self._cap_img(
                ("sec_n", w, h, radius),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["sec_btn_top"],
                bot_rgba=th["sec_btn_bot"],
                bd_a=th["sec_btn_bd"],
            )
            img_h = self._cap_img(
                ("sec_h", w, h, radius),
                w=w,
                h=h,
                radius=radius,
                top_rgba=th["sec_btn_hover_top"],
                bot_rgba=th["sec_btn_hover_bot"],
                bd_a=th["gold_btn_bd"],
            )
            fg = th["sec_btn_fg"]
            weight = "bold" if kind == "sec_bold" else "normal"

        tag = f"{tag_prefix}_{id(command)}_{cx}_{cy}"
        bg_id = cv.create_image(cx, cy, image=img_n, tags=(tag,))
        txt_id = cv.create_text(cx, cy, text=text, fill=fg, font=self._font(font_size, weight), tags=(tag,))

        def on_enter(_e):
            cv.configure(cursor="hand2")
            cv.itemconfigure(bg_id, image=img_h)

        def on_leave(_e):
            cv.configure(cursor="")
            cv.itemconfigure(bg_id, image=img_n)
            cv.coords(bg_id, cx, cy)
            cv.coords(txt_id, cx, cy)

        def on_press(_e):
            cv.coords(bg_id, cx, cy + 1)
            cv.coords(txt_id, cx, cy + 1)

        def on_release(_e):
            cv.coords(bg_id, cx, cy)
            cv.coords(txt_id, cx, cy)
            command()

        cv.tag_bind(tag, "<Enter>", on_enter)
        cv.tag_bind(tag, "<Leave>", on_leave)
        cv.tag_bind(tag, "<ButtonPress-1>", on_press)
        cv.tag_bind(tag, "<ButtonRelease-1>", on_release)
        return bg_id, txt_id

    def _build_titlebar(self, cv: tk.Canvas, W: int) -> None:
        th = self.th
        # Drag hitbox across custom titlebar
        drag_id = cv.create_rectangle(0, 0, W - 138, 44, fill="", outline="", tags=("title_drag",))

        mini_crest = self._crest_img(24)
        cv.create_image(30, 22, image=mini_crest, tags=("title_drag",))
        cv.create_text(30, 22, text="T", fill="#FFFFFF", font=self._font(8, "bold"), tags=("title_drag",))
        cv.create_text(
            48,
            22,
            text="TopStar2 Modifier",
            fill=th["text_sub"],
            font=self._font(9, "bold"),
            anchor="w",
            tags=("title_drag",),
        )
        cv.create_text(
            174,
            22,
            text=f"✦  {t('旗舰高定版')}",
            fill=th["gold_bright"],
            font=self._font(8, "bold"),
            anchor="w",
            tags=("title_drag",),
        )

        def start_drag(e):
            if self._is_maximized:
                return
            self._drag_origin = (e.x_root, e.y_root, self.winfo_x(), self.winfo_y())

        def do_drag(e):
            if self._drag_origin is None or self._is_maximized:
                return
            ox, oy, wx, wy = self._drag_origin
            nx = wx + (e.x_root - ox)
            ny = wy + (e.y_root - oy)
            self.geometry(f"{self.cur_w}x{self.cur_h}+{nx}+{ny}")

        def stop_drag(_e):
            self._drag_origin = None

        cv.tag_bind("title_drag", "<ButtonPress-1>", start_drag)
        cv.tag_bind("title_drag", "<B1-Motion>", do_drag)
        cv.tag_bind("title_drag", "<ButtonRelease-1>", stop_drag)
        cv.tag_bind("title_drag", "<Double-Button-1>", lambda _e: self._toggle_maximize())
        let_drag = drag_id  # keep reference alive
        _ = let_drag

        # Window Control Buttons (Minimize, Maximize/Restore, Close)
        win_specs = [
            (W - 108, "—", self._minimize_window, False),
            (W - 68, "❐" if self._is_maximized else "▢", self._toggle_maximize, False),
            (W - 28, "✕", self._request_close, True),
        ]
        img_idle = self._cap_img(
            ("wctrl_i",), w=34, h=26, radius=7, top_rgba=(0, 0, 0, 0), bot_rgba=(0, 0, 0, 0), bd_a=(0, 0, 0, 0), top_shine=False
        )
        img_hov = self._cap_img(
            ("wctrl_h",),
            w=34,
            h=26,
            radius=7,
            top_rgba=th["sec_btn_hover_top"],
            bot_rgba=th["sec_btn_hover_bot"],
            bd_a=th["sec_btn_bd"],
            top_shine=False,
        )
        img_close = self._cap_img(
            ("wctrl_c",),
            w=34,
            h=26,
            radius=7,
            top_rgba=(224, 52, 76, 245),
            bot_rgba=(186, 32, 56, 245),
            bd_a=(255, 156, 172, 220),
            top_shine=False,
        )

        for cx, sym, cmd, is_close in win_specs:
            wt_tag = f"wctrl_{cx}"
            b_id = cv.create_image(cx, 22, image=img_idle, tags=(wt_tag,))
            t_id = cv.create_text(cx, 22, text=sym, fill=th["text_sub"], font=self._font(9, "bold"), tags=(wt_tag,))

            def w_enter(_e, bi=b_id, ti=t_id, cl=is_close):
                cv.configure(cursor="hand2")
                cv.itemconfigure(bi, image=img_close if cl else img_hov)
                cv.itemconfigure(ti, fill="#FFFFFF" if cl else th["text_title"])

            def w_leave(_e, bi=b_id, ti=t_id):
                cv.configure(cursor="")
                cv.itemconfigure(bi, image=img_idle)
                cv.itemconfigure(ti, fill=th["text_sub"])

            cv.tag_bind(wt_tag, "<Enter>", w_enter)
            cv.tag_bind(wt_tag, "<Leave>", w_leave)
            cv.tag_bind(wt_tag, "<ButtonRelease-1>", lambda _e, c=cmd: c())

    def _build_hero_card(self, cv: tk.Canvas, box: tuple[int, int, int, int, int]) -> None:
        th = self.th
        bx, by, bw, _, _ = box

        # 52x52 Jewel Royal Crest + TS2 Monogram
        crest = self._crest_img(52)
        cv.create_image(bx + 46, by + 42, image=crest)
        cv.create_text(
            bx + 46,
            by + 43,
            text="TS2",
            fill="#FFFFFF",
            font=self._font(11, "bold"),
        )

        cv.create_text(
            bx + 84,
            by + 42,
            text=t("TopStar2修改器"),
            fill=th["text_title"],
            font=self._font(15, "bold"),
            anchor="w",
        )

        # Summary Medallion right next to title
        med_cx = bx + (342 if i18n.is_chinese() else 378)
        self._summary_bg_id = cv.create_image(med_cx, by + 42)
        self._summary_txt_id = cv.create_text(med_cx, by + 42, font=self._font(8, "bold"))

        # Top-right Theme & Language Haute Pills
        right_edge = bx + bw - 24
        self._canvas_btn(
            cv,
            right_edge - 42,
            by + 42,
            84,
            32,
            "English" if i18n.is_chinese() else "中文",
            self._toggle_language,
            kind="sec_bold",
            radius=10,
        )
        theme_label = f"☀  {t('珍珠瓷白')}" if th["is_dark"] else f"☾  {t('午夜星河')}"
        self._canvas_btn(
            cv,
            right_edge - 156,
            by + 42,
            128,
            32,
            theme_label,
            self._toggle_theme,
            kind="gold",
            radius=10,
        )

        # Recessed Velvet/Porcelain Path Vault Row
        vy = by + 95
        cv.create_text(
            bx + 24,
            vy,
            text=t("游戏根目录"),
            fill=th["text_sub"],
            font=self._font(9, "bold"),
            anchor="w",
        )

        vx_start = bx + (108 if i18n.is_chinese() else 148)
        vx_end = right_edge - 196
        vw = max(320, vx_end - vx_start)
        vh = 38
        vcx = vx_start + vw // 2

        vault_n = self._cap_img(
            ("vault_n", vw, vh),
            w=vw,
            h=vh,
            radius=11,
            top_rgba=th["vault_top"],
            bot_rgba=th["vault_bot"],
            bd_a=th["vault_bd"],
            top_shine=False,
        )
        vault_f = self._cap_img(
            ("vault_f", vw, vh),
            w=vw,
            h=vh,
            radius=11,
            top_rgba=th["vault_top"],
            bot_rgba=th["vault_bot"],
            bd_a=th["vault_focus_bd"],
            top_shine=False,
        )
        v_bg_id = cv.create_image(vcx, vy, image=vault_n)
        cv.create_image(vx_start + 20, vy, image=self._folder_img(18))

        path_ent = tk.Entry(
            cv,
            textvariable=self.path,
            bg=th["entry_bg"],
            fg=th["entry_fg"],
            insertbackground=th["entry_caret"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=self._font(9),
        )
        cv.create_window(vx_start + 38, vy, window=path_ent, anchor="w", width=vw - 52, height=22)
        path_ent.bind("<FocusIn>", lambda _e: cv.itemconfigure(v_bg_id, image=vault_f))
        path_ent.bind("<FocusOut>", lambda _e: cv.itemconfigure(v_bg_id, image=vault_n))

        self._canvas_btn(cv, right_edge - 140, vy, 92, 36, f"✦  {t('浏览')}", self.browse, kind="gold", radius=10)
        self._canvas_btn(cv, right_edge - 42, vy, 84, 36, t("读取"), self.read_status, kind="sec_bold", radius=10)

        if not self.file_path.get():
            self.file_path.set(t("选择游戏根目录后点击「读取」，或直接将游戏目录拖拽至此窗口"))
        self._file_txt_id = cv.create_text(
            bx + 24,
            by + 128,
            text=self.file_path.get(),
            fill=th["text_muted"],
            font=self._font(8),
            anchor="w",
        )

    def _build_sidebar(self, cv: tk.Canvas, box: tuple[int, int, int, int, int]) -> None:
        th = self.th
        sx, sy, sw, sh, _ = box
        cv.create_text(
            sx + 22,
            sy + 26,
            text=f"✦  {t('功能分类')}",
            fill=th["gold_bright"],
            font=self._font(8, "bold"),
            anchor="w",
        )

        self._nav_ui: dict[str, dict] = {}
        nw, nh = sw - 32, 66
        ncx = sx + sw // 2

        img_idle = self._cap_img(
            ("nav_i", nw, nh),
            w=nw,
            h=nh,
            radius=13,
            top_rgba=th["nav_idle_top"],
            bot_rgba=th["nav_idle_bot"],
            bd_a=th["nav_idle_bd"],
            top_shine=False,
        )
        img_hov = self._cap_img(
            ("nav_h", nw, nh),
            w=nw,
            h=nh,
            radius=13,
            top_rgba=th["nav_hover_top"],
            bot_rgba=th["nav_hover_bot"],
            bd_a=th["nav_hover_bd"],
        )
        img_act = self._cap_img(
            ("nav_a", nw, nh),
            w=nw,
            h=nh,
            radius=13,
            top_rgba=th["nav_act_top"],
            bot_rgba=th["nav_act_bot"],
            bd_a=th["nav_act_bd_a"],
            bd_b=th["nav_act_bd_b"],
            left_gold_bar=th["horizon_gold"] + (245,),
        )
        orb_idle = self._cap_img(
            ("orb_i",),
            w=36,
            h=36,
            radius=10,
            top_rgba=th["sec_btn_top"],
            bot_rgba=th["sec_btn_bot"],
            bd_a=th["sec_btn_bd"],
            top_shine=False,
        )
        orb_act = self._cap_img(
            ("orb_a",),
            w=36,
            h=36,
            radius=10,
            top_rgba=th["cta_a"] + (245,),
            bot_rgba=th["cta_b"] + (245,),
            bd_a=th["cta_rim_a"],
            bd_b=th["cta_rim_b"],
        )
        cnt_idle = self._cap_img(
            ("ncnt_i",),
            w=44,
            h=22,
            radius=11,
            top_rgba=th["vault_top"],
            bot_rgba=th["vault_bot"],
            bd_a=th["nav_idle_bd"],
            top_shine=False,
        )
        cnt_act = self._cap_img(
            ("ncnt_a",),
            w=44,
            h=22,
            radius=11,
            top_rgba=th["gold_btn_top"],
            bot_rgba=th["gold_btn_bot"],
            bd_a=th["gold_btn_bd"],
            top_shine=False,
        )

        for idx, cat in enumerate(CATEGORIES):
            cid = cat["id"]
            ncy = sy + 78 + idx * 74
            ntag = f"nav_{cid}"

            bg_id = cv.create_image(ncx, ncy, image=img_idle, tags=(ntag,))
            orb_id = cv.create_image(sx + 44, ncy, image=orb_idle, tags=(ntag,))
            ico_id = cv.create_text(sx + 44, ncy, text=cat["icon"], fill=th["text_sub"], font=self._font(11, "bold"), tags=(ntag,))
            ttl_id = cv.create_text(
                sx + 72,
                ncy - 9,
                text=t(cat["title"]),
                fill=th["text_primary"],
                font=self._font(9, "bold"),
                anchor="w",
                tags=(ntag,),
            )
            sub_id = cv.create_text(
                sx + 72,
                ncy + 11,
                text=t(cat["sub"]),
                fill=th["text_muted"],
                font=self._font(8),
                anchor="w",
                tags=(ntag,),
            )
            cbg_id = cv.create_image(sx + sw - 44, ncy, image=cnt_idle, tags=(ntag,))
            ctxt_id = cv.create_text(sx + sw - 44, ncy, text="0/0", fill=th["text_muted"], font=self._mono(8), tags=(ntag,))

            def n_enter(_e, c=cid, bi=bg_id):
                cv.configure(cursor="hand2")
                if self.active_tab != c:
                    cv.itemconfigure(bi, image=img_hov)

            def n_leave(_e, c=cid, bi=bg_id):
                cv.configure(cursor="")
                if self.active_tab != c:
                    cv.itemconfigure(bi, image=img_idle)

            cv.tag_bind(ntag, "<Enter>", n_enter)
            cv.tag_bind(ntag, "<Leave>", n_leave)
            cv.tag_bind(ntag, "<ButtonRelease-1>", lambda _e, c=cid: self._select_tab(c))

            self._nav_ui[cid] = {
                "cat": cat,
                "bg": bg_id,
                "orb": orb_id,
                "ico": ico_id,
                "ttl": ttl_id,
                "sub": sub_id,
                "cbg": cbg_id,
                "ctxt": ctxt_id,
                "img_idle": img_idle,
                "img_act": img_act,
                "orb_idle": orb_idle,
                "orb_act": orb_act,
                "cnt_idle": cnt_idle,
                "cnt_act": cnt_act,
            }

        # Bottom Quick Actions
        qy_cap = sy + sh - 68
        cv.create_text(sx + 22, qy_cap, text=t("快捷操作"), fill=th["text_muted"], font=self._font(8, "bold"), anchor="w")
        qy_btn = sy + sh - 34
        self._canvas_btn(cv, sx + 74, qy_btn, 108, 32, t("全选本页"), lambda: self._set_page_locks(True), kind="sec_bold", font_size=8, radius=9)
        self._canvas_btn(cv, sx + sw - 74, qy_btn, 108, 32, t("清空本页"), lambda: self._set_page_locks(False), kind="secondary", font_size=8, radius=9)

        self._sync_nav_visuals()

    def _sync_nav_visuals(self) -> None:
        th = self.th
        for cid, ui in self._nav_ui.items():
            act = cid == self.active_tab
            self.cv.itemconfigure(ui["bg"], image=ui["img_act"] if act else ui["img_idle"])
            self.cv.itemconfigure(ui["orb"], image=ui["orb_act"] if act else ui["orb_idle"])
            self.cv.itemconfigure(ui["ico"], fill="#FFFFFF" if act else th["text_sub"])
            self.cv.itemconfigure(ui["ttl"], fill=th["text_title"] if act else th["text_primary"])
            self.cv.itemconfigure(ui["cbg"], image=ui["cnt_act"] if act else ui["cnt_idle"])
            self.cv.itemconfigure(ui["ctxt"], fill=th["gold_btn_fg"] if act else th["text_muted"])

    def _build_footer(self, cv: tk.Canvas, box: tuple[int, int, int, int, int]) -> None:
        th = self.th
        fx, fy, fw, fh, _ = box
        cy = fy + fh // 2
        cv.create_text(fx + 24, cy, text="❖", fill=th["gold_bright"], font=self._font(10, "bold"), anchor="w")
        cv.create_text(
            fx + 46,
            cy,
            text=t("退出游戏后修改并点击「应用修改」生效 · 首次写入自动备份 .bak（不覆盖已有备份）"),
            fill=th["text_sub"],
            font=self._font(8),
            anchor="w",
        )
        self._canvas_btn(
            cv,
            fx + fw - 98,
            cy,
            158,
            38,
            f"✦  {t('应用修改')}",
            self.apply,
            kind="primary",
            font_size=10,
            radius=11,
        )

    # ==========================================================================
    # Right Feature Gallery Page Renderer
    # ==========================================================================
    def _select_tab(self, cid: str) -> None:
        if self.active_tab == cid:
            return
        self.active_tab = cid
        self._sync_nav_visuals()
        self._render_active_page()

    def _render_active_page(self) -> None:
        cv = self.cv
        th = self.th
        cv.delete("page_item")
        for r in self.rows.values():
            r["cv_badge"] = None
            r["ui_sync"] = None

        mx, my, mw, _, _ = self._layout_boxes[2]
        cat = next(c for c in CATEGORIES if c["id"] == self.active_tab)

        # Header
        cv.create_text(
            mx + 26,
            my + 28,
            text=f"{cat['icon']}  {t(cat['title'])}",
            fill=th["text_title"],
            font=self._font(13, "bold"),
            anchor="w",
            tags=("page_item",),
        )
        cv.create_text(
            mx + mw - 26,
            my + 29,
            text=t(cat["desc"]),
            fill=th["text_muted"],
            font=self._font(8),
            anchor="e",
            tags=("page_item",),
        )

        flag_map = {s["key"]: s for s in FLAGS + OTHER_FLAGS}
        hold_map = {s["key"]: s for s in HOLDS}
        hold_map["play"] = PLAY_SPEC

        rw = mw - 44
        rcx = mx + mw // 2
        keys = cat["keys"]
        if len(keys) >= 8:
            rh, gap, top_pad = 48, 5, 58
        elif len(keys) >= 7:
            rh, gap, top_pad = 54, 6, 66
        else:
            rh, gap, top_pad = 60, 9, 66
        start_y = my + top_pad + rh // 2

        for idx, key in enumerate(keys):
            rcy = start_y + idx * (rh + gap)
            if key == "fps":
                self._draw_fps_row(cv, rcx, rcy, rw, rh)
            elif key in hold_map:
                self._draw_timer_row(cv, key, hold_map[key], rcx, rcy, rw, rh)
            else:
                self._draw_flag_row(cv, key, flag_map[key], rcx, rcy, rw, rh)

    def _row_capsule_imgs(self, rw: int, rh: int, is_hero: bool = False) -> tuple[tk.PhotoImage, tk.PhotoImage, tk.PhotoImage]:
        th = self.th
        if is_hero:
            hero_n = self._cap_img(
                ("r_hero_n", rw, rh),
                w=rw,
                h=rh,
                radius=13,
                top_rgba=th["row_hero_top"],
                bot_rgba=th["row_hero_bot"],
                bd_a=th["row_hero_bd_a"],
                bd_b=th["row_hero_bd_b"],
            )
            hero_h = self._cap_img(
                ("r_hero_h", rw, rh),
                w=rw,
                h=rh,
                radius=13,
                top_rgba=th["row_hover_top"],
                bot_rgba=th["row_hero_bot"],
                bd_a=(252, 224, 154, 240),
                bd_b=th["row_hero_bd_b"],
            )
            return hero_n, hero_n, hero_h

        img_on = self._cap_img(
            ("r_on", rw, rh),
            w=rw,
            h=rh,
            radius=12,
            top_rgba=th["row_on_top"],
            bot_rgba=th["row_on_bot"],
            bd_a=th["row_on_bd"],
        )
        img_off = self._cap_img(
            ("r_off", rw, rh),
            w=rw,
            h=rh,
            radius=12,
            top_rgba=th["row_off_top"],
            bot_rgba=th["row_off_bot"],
            bd_a=th["row_off_bd"],
            top_shine=False,
        )
        img_hov = self._cap_img(
            ("r_hov", rw, rh),
            w=rw,
            h=rh,
            radius=12,
            top_rgba=th["row_hover_top"],
            bot_rgba=th["row_hover_bot"],
            bd_a=th["row_hover_bd"],
        )
        return img_on, img_off, img_hov

    def _draw_badge_on_canvas(self, cv: tk.Canvas, key: str, cx: int, cy: int) -> tuple[int, int]:
        th = self.th
        row = self.rows[key]
        kind = row["badge_kind"]
        text = row["badge_text"]

        bg_id = cv.create_image(cx, cy, tags=("page_item",))
        txt_id = cv.create_text(cx, cy, font=self._font(8, "bold"), tags=("page_item",))
        row["cv_badge"] = (bg_id, txt_id)
        self._apply_badge_visual(key)
        _ = th, kind, text
        return bg_id, txt_id

    def _apply_badge_visual(self, key: str) -> None:
        row = self.rows[key]
        pair = row.get("cv_badge")
        if not pair:
            return
        bg_id, txt_id = pair
        if not hasattr(self, "cv") or not self.cv.winfo_exists():
            return
        th = self.th
        kind = row["badge_kind"]
        text = row["badge_text"]
        if kind == "idle" or not text:
            self.cv.itemconfigure(bg_id, image="")
            self.cv.itemconfigure(txt_id, text="")
            return
        if kind == "locked":
            img = self._cap_img(
                ("bdg_on",),
                w=98,
                h=25,
                radius=12,
                top_rgba=th["badge_on_top"],
                bot_rgba=th["badge_on_bot"],
                bd_a=th["badge_on_bd"],
                top_shine=False,
            )
            self.cv.itemconfigure(bg_id, image=img)
            self.cv.itemconfigure(txt_id, text=f"✦ {text}", fill=th["badge_on_fg"])
        elif kind == "open":
            img = self._cap_img(
                ("bdg_op",),
                w=74,
                h=24,
                radius=12,
                top_rgba=th["badge_orig_bg"],
                bot_rgba=th["badge_orig_bg"],
                bd_a=th["badge_orig_bd"],
                top_shine=False,
            )
            self.cv.itemconfigure(bg_id, image=img)
            self.cv.itemconfigure(txt_id, text=text, fill=th["badge_orig_fg"])
        else:
            img = self._cap_img(
                ("bdg_wn",),
                w=88,
                h=25,
                radius=12,
                top_rgba=th["badge_warn_bg"],
                bot_rgba=th["badge_warn_bg"],
                bd_a=th["badge_warn_bd"],
                top_shine=False,
            )
            self.cv.itemconfigure(bg_id, image=img)
            self.cv.itemconfigure(txt_id, text=text, fill=th["badge_warn_fg"])

    def _bind_row_switch(
        self,
        cv: tk.Canvas,
        key: str,
        sw_cx: int,
        sw_cy: int,
        row_bg_id: int,
        pip_id: int | None,
        img_on: tk.PhotoImage,
        img_off: tk.PhotoImage,
        img_hov: tk.PhotoImage,
        click_tag: str,
    ) -> None:
        th = self.th
        row = self.rows[key]
        lock_var: tk.BooleanVar = row["lock"]
        row["anim_step"] = 4 if lock_var.get() else 0
        sw_id = cv.create_image(sw_cx, sw_cy, image=self._sw_img(row["anim_step"], False), tags=("page_item", click_tag))
        state = {"hover": False}

        def sync_row_surface():
            is_on = lock_var.get()
            if state["hover"]:
                cv.itemconfigure(row_bg_id, image=img_hov)
            else:
                cv.itemconfigure(row_bg_id, image=img_on if is_on else img_off)
            if pip_id is not None:
                cv.itemconfigure(pip_id, fill=th["pip_on"] if is_on else th["text_muted"])

        def animate_step():
            if not cv.winfo_exists():
                return
            items = cv.find_withtag(click_tag)
            if not items:
                row["anim_job"] = None
                return
            target = 4 if lock_var.get() else 0
            if row["anim_step"] < target:
                row["anim_step"] += 1
            elif row["anim_step"] > target:
                row["anim_step"] -= 1
            cv.itemconfigure(sw_id, image=self._sw_img(row["anim_step"], state["hover"]))
            if row["anim_step"] != target:
                row["anim_job"] = self.after(14, animate_step)
            else:
                row["anim_job"] = None

        def toggle_now(_e=None):
            lock_var.set(not lock_var.get())
            self._on_lock_changed(key)

        row["ui_sync"] = lambda: (sync_row_surface(), animate_step())
        sync_row_surface()

        def on_enter(_e):
            state["hover"] = True
            cv.configure(cursor="hand2")
            sync_row_surface()
            cv.itemconfigure(sw_id, image=self._sw_img(row["anim_step"], True))

        def on_leave(_e):
            state["hover"] = False
            cv.configure(cursor="")
            sync_row_surface()
            cv.itemconfigure(sw_id, image=self._sw_img(row["anim_step"], False))

        cv.tag_bind(click_tag, "<Enter>", on_enter)
        cv.tag_bind(click_tag, "<Leave>", on_leave)
        cv.tag_bind(click_tag, "<ButtonRelease-1>", toggle_now)

    def _on_lock_changed(self, key: str) -> None:
        row = self.rows.get(key)
        if row and callable(row.get("ui_sync")):
            row["ui_sync"]()
        self._refresh_summary_and_counts()

    def _draw_flag_row(self, cv: tk.Canvas, key: str, spec: dict, rcx: int, rcy: int, rw: int, rh: int) -> None:
        th = self.th
        left_x = rcx - rw // 2
        right_x = rcx + rw // 2
        rtag = f"row_{key}"
        img_on, img_off, img_hov = self._row_capsule_imgs(rw, rh)

        bg_id = cv.create_image(rcx, rcy, image=img_off, tags=("page_item", rtag))
        pip_id = cv.create_oval(left_x + 18, rcy - 12, left_x + 24, rcy - 6, fill=th["text_muted"], outline="", tags=("page_item", rtag))
        cv.create_text(
            left_x + 32,
            rcy - 9,
            text=t(spec["title"]),
            fill=th["text_primary"],
            font=self._font(9, "bold"),
            anchor="w",
            tags=("page_item", rtag),
        )
        cv.create_text(
            left_x + 32,
            rcy + 11,
            text=t(spec["detail"]),
            fill=th["text_muted"],
            font=self._font(8),
            anchor="w",
            tags=("page_item", rtag),
        )

        self._draw_badge_on_canvas(cv, key, right_x - 126, rcy)
        self._bind_row_switch(cv, key, right_x - 38, rcy, bg_id, pip_id, img_on, img_off, img_hov, rtag)

    def _draw_timer_row(self, cv: tk.Canvas, key: str, spec: dict, rcx: int, rcy: int, rw: int, rh: int) -> None:
        th = self.th
        left_x = rcx - rw // 2
        right_x = rcx + rw // 2
        rtag = f"row_{key}"
        img_on, img_off, img_hov = self._row_capsule_imgs(rw, rh)

        bg_id = cv.create_image(rcx, rcy, image=img_off, tags=("page_item", rtag))
        pip_id = cv.create_oval(left_x + 18, rcy - 12, left_x + 24, rcy - 6, fill=th["text_muted"], outline="", tags=("page_item", rtag))
        cv.create_text(
            left_x + 32,
            rcy - 9,
            text=t(spec["title"]),
            fill=th["text_primary"],
            font=self._font(9, "bold"),
            anchor="w",
            tags=("page_item", rtag),
        )
        cv.create_text(
            left_x + 32,
            rcy + 11,
            text=t(spec["detail"]),
            fill=th["text_muted"],
            font=self._font(8),
            anchor="w",
            tags=("page_item", rtag),
        )

        # Sculpted seconds input capsule
        ecx = right_x - 236
        ew, eh = 64, 30
        e_n = self._cap_img(("t_ent_n",), w=ew, h=eh, radius=9, top_rgba=th["vault_top"], bot_rgba=th["vault_bot"], bd_a=th["vault_bd"], top_shine=False)
        e_f = self._cap_img(("t_ent_f",), w=ew, h=eh, radius=9, top_rgba=th["vault_top"], bot_rgba=th["vault_bot"], bd_a=th["vault_focus_bd"], top_shine=False)
        ebg_id = cv.create_image(ecx, rcy, image=e_n, tags=("page_item",))
        ent = tk.Entry(
            cv,
            textvariable=self.rows[key]["seconds"],
            justify="center",
            bg=th["entry_bg"],
            fg=th["entry_fg"],
            insertbackground=th["entry_caret"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=self._mono(10),
        )
        cv.create_window(ecx, rcy, window=ent, width=ew - 18, height=20, tags=("page_item",))
        ent.bind("<FocusIn>", lambda _e, i=ebg_id: cv.itemconfigure(i, image=e_f))
        ent.bind("<FocusOut>", lambda _e, i=ebg_id: cv.itemconfigure(i, image=e_n))
        cv.create_text(ecx + 42, rcy, text=t("秒"), fill=th["text_muted"], font=self._font(8), anchor="w", tags=("page_item",))

        self._draw_badge_on_canvas(cv, key, right_x - 126, rcy)
        self._bind_row_switch(cv, key, right_x - 38, rcy, bg_id, pip_id, img_on, img_off, img_hov, rtag)

    def _draw_fps_row(self, cv: tk.Canvas, rcx: int, rcy: int, rw: int, rh: int) -> None:
        th = self.th
        left_x = rcx - rw // 2
        right_x = rcx + rw // 2
        rtag = "row_fps"
        img_on, img_off, img_hov = self._row_capsule_imgs(rw, rh, is_hero=True)

        bg_id = cv.create_image(rcx, rcy, image=img_on, tags=("page_item", rtag))
        cv.create_text(
            left_x + 18,
            rcy - 9,
            text=f"✦  {t('高刷与高帧率')}",
            fill=th["gold_bright"] if th["is_dark"] else th["iris_bright"],
            font=self._font(9, "bold"),
            anchor="w",
            tags=("page_item", rtag),
        )
        cv.create_text(
            left_x + 18,
            rcy + 11,
            text=t("解锁 120/240Hz 刷新率与帧率限制，不影响游戏速度。"),
            fill=th["text_sub"],
            font=self._font(8),
            anchor="w",
            tags=("page_item", rtag),
        )

        # Segmented Rocker [ 120Hz | 240Hz ]
        tray_cx = right_x - 252
        tray_img = self._cap_img(
            ("fps_tray",),
            w=134,
            h=32,
            radius=10,
            top_rgba=th["vault_top"],
            bot_rgba=th["vault_bot"],
            bd_a=th["vault_bd"],
            top_shine=False,
        )
        cv.create_image(tray_cx, rcy, image=tray_img, tags=("page_item",))

        sel_on = self._cap_img(
            ("fps_sel_on",),
            w=62,
            h=26,
            radius=8,
            top_rgba=th["cta_a"] + (255,),
            bot_rgba=th["cta_b"] + (255,),
            bd_a=th["cta_rim_a"],
            bd_b=th["cta_rim_b"],
        )
        sel_dim = self._cap_img(
            ("fps_sel_dim",),
            w=62,
            h=26,
            radius=8,
            top_rgba=th["sec_btn_top"],
            bot_rgba=th["sec_btn_bot"],
            bd_a=th["sec_btn_bd"],
            top_shine=False,
        )
        unsel = self._cap_img(
            ("fps_unsel",),
            w=62,
            h=26,
            radius=8,
            top_rgba=(0, 0, 0, 0),
            bot_rgba=(0, 0, 0, 0),
            bd_a=(0, 0, 0, 0),
            top_shine=False,
        )

        fps_var: tk.StringVar = self.rows["fps"]["seconds"]
        lock_var: tk.BooleanVar = self.rows["fps"]["lock"]
        seg_ids: dict[str, tuple[int, int]] = {}

        for idx_v, val in enumerate(("120", "240")):
            scx = tray_cx - 32 + idx_v * 64
            stag = f"fps_opt_{val}"
            sb = cv.create_image(scx, rcy, image=unsel, tags=("page_item", stag))
            st = cv.create_text(scx, rcy, text=f"{val}Hz", font=self._mono(9), tags=("page_item", stag))
            seg_ids[val] = (sb, st)

            def pick(_e, v=val):
                fps_var.set(v)
                if not lock_var.get():
                    lock_var.set(True)
                    self._on_lock_changed("fps")
                else:
                    sync_seg()

            cv.tag_bind(stag, "<Enter>", lambda _e: cv.configure(cursor="hand2"))
            cv.tag_bind(stag, "<Leave>", lambda _e: cv.configure(cursor=""))
            cv.tag_bind(stag, "<ButtonRelease-1>", pick)

        def sync_seg():
            if not cv.winfo_exists():
                return
            cur = fps_var.get()
            on = lock_var.get()
            for val, (sb, st) in seg_ids.items():
                if not cv.find_withtag(f"fps_opt_{val}"):
                    return
                if val == cur:
                    cv.itemconfigure(sb, image=sel_on if on else sel_dim)
                    cv.itemconfigure(st, fill="#FFFFFF" if on else th["text_sub"])
                else:
                    cv.itemconfigure(sb, image=unsel)
                    cv.itemconfigure(st, fill=th["text_muted"])

        self._draw_badge_on_canvas(cv, "fps", right_x - 126, rcy)
        self._bind_row_switch(cv, "fps", right_x - 38, rcy, bg_id, None, img_on, img_off, img_hov, rtag)
        prev_sync = self.rows["fps"]["ui_sync"]
        self.rows["fps"]["ui_sync"] = lambda: (prev_sync(), sync_seg())
        sync_seg()

    # ==========================================================================
    # State Sync, Theme/Language Switching & Patch Actions
    # ==========================================================================
    def _set_badge_model(self, key: str, text: str, kind: str) -> None:
        self.rows[key]["badge_kind"] = kind
        self.rows[key]["badge_text"] = text
        self._apply_badge_visual(key)

    def _refresh_summary_and_counts(self) -> None:
        if not hasattr(self, "cv") or not self.cv.winfo_exists():
            return
        th = self.th
        total_on = 0
        total_all = 0
        for cid, ui in self._nav_ui.items():
            keys = ui["cat"]["keys"]
            on_cnt = sum(1 for k in keys if self.rows[k]["lock"].get())
            self.cv.itemconfigure(ui["ctxt"], text=f"{on_cnt}/{len(keys)}")
            total_on += on_cnt
            total_all += len(keys)

        if self._last_found is not None:
            med_img = self._cap_img(
                ("med_rdy",),
                w=204,
                h=28,
                radius=14,
                top_rgba=th["gold_btn_top"],
                bot_rgba=th["gold_btn_bot"],
                bd_a=th["gold_btn_bd"],
                top_shine=False,
            )
            self.cv.itemconfigure(self._summary_bg_id, image=med_img)
            self.cv.itemconfigure(
                self._summary_txt_id,
                text=f"✦  {t('已就绪 · {on} / {total} 项启用', on=total_on, total=total_all)}",
                fill=th["gold_btn_fg"],
            )
        else:
            med_img = self._cap_img(
                ("med_wait",),
                w=172,
                h=28,
                radius=14,
                top_rgba=th["sec_btn_top"],
                bot_rgba=th["sec_btn_bot"],
                bd_a=th["sec_btn_bd"],
                top_shine=False,
            )
            self.cv.itemconfigure(self._summary_bg_id, image=med_img)
            self.cv.itemconfigure(
                self._summary_txt_id,
                text=f"✧  {t('待载入游戏目录')}",
                fill=th["text_sub"],
            )

    def _set_page_locks(self, value: bool) -> None:
        cat = next((c for c in CATEGORIES if c["id"] == self.active_tab), None)
        if not cat:
            return
        for k in cat["keys"]:
            self.rows[k]["lock"].set(value)
            if callable(self.rows[k].get("ui_sync")):
                self.rows[k]["ui_sync"]()
        self._refresh_summary_and_counts()

    def _toggle_theme(self) -> None:
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        _save_theme_pref(self.theme_mode)
        self._setup_icon()
        self._build_canvas_ui()

    def _toggle_language(self) -> None:
        i18n.toggle_language()
        if self._last_path is None:
            self.file_path.set(t("选择游戏根目录后点击「读取」，或直接将游戏目录拖拽至此窗口"))
        else:
            self.file_path.set(t("文件：{path}", path=self._last_path))
        for r in self.rows.values():
            r["cv_badge"] = None
            r["ui_sync"] = None
        if self._last_path is not None and self._last_found is not None:
            self._update_models_from_found(self._last_found, sync_inputs=False)
        self._build_canvas_ui()

    def browse(self) -> None:
        picked = filedialog.askdirectory(title=t("选择游戏根目录"))
        if picked:
            self.path.set(picked)
            self.read_status()

    def _set_file_status(self, text: str) -> None:
        self.file_path.set(text)
        if hasattr(self, "cv") and self.cv.winfo_exists() and hasattr(self, "_file_txt_id"):
            self.cv.itemconfigure(self._file_txt_id, text=text)

    def _ensure_decrypted_dll(self) -> Path | None:
        text = self.path.get().strip()
        if not text:
            messagebox.showerror(t("TopStar2修改器"), t("先点「浏览」，选择游戏根目录。"))
            return None
        root = Path(text)
        if not root.is_dir():
            messagebox.showerror(t("TopStar2修改器"), t("请选择游戏根目录，不是单个文件。"))
            return None
        path = find_dll(root)
        if path is None:
            messagebox.showerror(
                t("TopStar2修改器"),
                t("这个目录里没有 Game\\TopStar2_Data\\Managed\\Assembly-CSharp.dll。\n请选游戏根目录。"),
            )
            return None
        try:
            data = path.read_bytes()
        except OSError as exc:
            messagebox.showerror(t("TopStar2修改器"), t("读不了这个文件。先退出游戏。\n{exc}", exc=exc))
            return None

        if is_encrypted_dll(data):
            self._set_file_status(t("检测到原版加密 DLL，正在自动解密（会短暂启动一次游戏进程）…"))
            self.update_idletasks()
            try:
                decrypted = decrypt_via_game(root, path, len(data))
                bak = bak_path(path)
                if not bak.exists():
                    shutil.copy2(path, bak)
                path.write_bytes(decrypted)
            except OSError as exc:
                messagebox.showerror(t("TopStar2修改器"), t("自动解密失败：{exc}", exc=exc))
                return None
        return path

    def _update_models_from_found(self, found: dict, sync_inputs: bool = True) -> None:
        for spec in FLAGS + OTHER_FLAGS:
            key = spec["key"]
            state = found.get(key, {}).get("state", "unknown")
            if state == "open":
                self._set_badge_model(key, t("原版"), "open")
            elif state == "locked":
                self._set_badge_model(key, t("已生效"), "locked")
            else:
                self._set_badge_model(key, t("不匹配"), "unknown")
            if sync_inputs:
                self.rows[key]["lock"].set(state == "locked")

        for spec in HOLDS:
            key = spec["key"]
            item = found.get(key, {"state": "unknown", "seconds": spec["default"]})
            state = item["state"]
            if state == "open":
                self._set_badge_model(key, t("倒计时开启"), "open")
            elif state == "locked":
                self._set_badge_model(key, t("停驻 {seconds}s", seconds=f"{item['seconds']:g}"), "locked")
            else:
                self._set_badge_model(key, t("不匹配"), "unknown")
            if sync_inputs:
                self.rows[key]["lock"].set(state == "locked")
                if state == "locked":
                    self.rows[key]["seconds"].set(f"{item['seconds']:g}")

        play = found.get("play", {"state": "unknown", "seconds": 90})
        if play["state"] == "open":
            self._set_badge_model("play", t("倒计时开启"), "open")
        elif play["state"] == "locked":
            self._set_badge_model("play", t("停驻 {seconds}s", seconds=f"{play['seconds']}"), "locked")
        else:
            self._set_badge_model("play", t("不匹配"), "unknown")
        if sync_inputs:
            self.rows["play"]["lock"].set(play["state"] == "locked")
            if play["state"] == "locked":
                self.rows["play"]["seconds"].set(str(play["seconds"]))

        fps_info = found.get("fps", {"state": "unknown", "seconds": 120})
        if fps_info["state"] == "open":
            self._set_badge_model("fps", t("原版"), "open")
        elif fps_info["state"] == "locked":
            fps_num = int(fps_info.get("seconds", 120))
            self._set_badge_model("fps", f"{fps_num}Hz", "locked")
        else:
            self._set_badge_model("fps", t("不匹配"), "unknown")
        if sync_inputs:
            self.rows["fps"]["lock"].set(fps_info["state"] == "locked")
            if fps_info["state"] == "locked":
                fps_num = int(fps_info.get("seconds", 120))
                self.rows["fps"]["seconds"].set(str(fps_num) if str(fps_num) in ("120", "240") else "120")

    def _render_found(self, path: Path, found: dict, sync_inputs: bool = True) -> None:
        self._set_file_status(t("文件：{path}", path=path))
        self._update_models_from_found(found, sync_inputs=sync_inputs)
        self._render_active_page()
        self._refresh_summary_and_counts()

    def read_status(self) -> None:
        path = self._ensure_decrypted_dll()
        if path is None:
            self._set_file_status(t("选择游戏根目录后点击「读取」，或直接将游戏目录拖拽至此窗口"))
            self._last_path = None
            self._last_found = None
            for key in self.rows:
                self._set_badge_model(key, "", "idle")
            self._render_active_page()
            self._refresh_summary_and_counts()
            return
        try:
            found = inspect_dll(path)
        except OSError as exc:
            messagebox.showerror(t("TopStar2修改器"), str(exc))
            return
        self._last_path = path
        self._last_found = found
        self._render_found(path, found, sync_inputs=True)

    def apply(self) -> None:
        path = self._ensure_decrypted_dll()
        if path is None:
            return

        lines = []
        try:
            for spec in HOLDS:
                row = self.rows[spec["key"]]
                if row["lock"].get():
                    sec = parse_seconds(row["seconds"].get(), spec["low"], spec["high"], spec["places"])
                    lines.append(f"{spec['key']}=1|{sec}")
                else:
                    lines.append(f"{spec['key']}=0")
            play_row = self.rows["play"]
            if play_row["lock"].get():
                sec = parse_seconds(play_row["seconds"].get(), 1, 999, 0)
                lines.append(f"play=1|{sec}")
            else:
                lines.append("play=0")
            for spec in FLAGS + OTHER_FLAGS:
                key = spec["key"]
                lines.append(f"{key}={'1' if self.rows[key]['lock'].get() else '0'}")
            fps_row = self.rows["fps"]
            if fps_row["lock"].get():
                lines.append(f"fps=1|{int(fps_row['seconds'].get())}")
            else:
                lines.append("fps=0")
        except ValueError as exc:
            messagebox.showerror(t("TopStar2修改器"), str(exc))
            return

        bak = bak_path(path)
        tmp_choices = None
        try:
            if not bak.exists():
                shutil.copy2(path, bak)
            if self.rows["fix_touch"]["lock"].get():
                pwt_src = ROOT / "PortableWindowsTouch.dll"
                pwt_dst = path.parent / "PortableWindowsTouch.dll"
                if pwt_src.is_file() and (
                    not pwt_dst.exists() or pwt_dst.read_bytes() != pwt_src.read_bytes()
                ):
                    shutil.copy2(pwt_src, pwt_dst)
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
                tf.write("\n".join(lines) + "\n")
                tmp_choices = Path(tf.name)
            out = run_patcher(["apply", str(path), str(tmp_choices)])
        except OSError as exc:
            messagebox.showerror(t("TopStar2修改器"), t("写不进去。先退出游戏。\n{exc}", exc=exc))
            return
        finally:
            if tmp_choices is not None:
                try:
                    tmp_choices.unlink(missing_ok=True)
                except OSError:
                    pass

        notes = [n for n in (format_note(line.strip()) for line in out.splitlines()) if n]
        if not notes:
            notes = [t("没有需要改的项")]
        self.read_status()
        messagebox.showinfo(t("TopStar2修改器"), t("已写入。重新启动游戏再生效。\n\n{notes}", notes="\n".join(notes)))


def main() -> None:
    app = App()
    app.protocol("WM_DELETE_WINDOW", app._request_close)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        err = traceback.format_exc()
        try:
            ctypes.windll.user32.MessageBoxW(None, err, "TopStar2 Modifier Error", 0x10)
        except Exception:
            print(err, file=sys.stderr)
        sys.exit(1)
