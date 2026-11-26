"""UI language helper. Chinese Windows defaults to Chinese; others default to English."""

from __future__ import annotations

import ctypes
import locale

_EN = {
    "TopStar2修改器": "TopStar2 Modifier",
    "游戏根目录": "Game Root Folder",
    "浏览": "Browse",
    "读取": "Read",
    "选择游戏根目录": "Select Game Root Folder",
    "文件：{path}": "File: {path}",
    "选歌解锁": "Song Unlocks",
    "物品与皮肤解锁": "Items & Note Unlocks",
    "倒计时": "Timers",
    "其他功能": "Other Options",
    "未读取文件": "No file loaded",
    "选择游戏根目录后点击「读取」": "Select the game root folder and click Read",
    "原版": "Original",
    "已改": "Patched",
    "不匹配": "Mismatch",
    "倒计时开启": "Active",
    "停在 {seconds} 秒": "{seconds}s",
    "播放教程": "Enabled",
    "已跳过": "Skipped",
    "已加兜底": "Patched",
    "未加兜底": "Original",
    "应用": "Apply",
    "秒": "s",
    "先退出游戏。点「浏览」选择游戏根目录。勾上再应用。取消勾选再应用，只还原这一项。文件大小不变。已有的 .bak 不会覆盖。": (
        "Exit the game first. Click Browse to select the game root folder. Check & Apply to patch; "
        "uncheck & Apply to revert. Existing .bak is never overwritten."
    ),
    "选歌": "Song Select",
    "大于 85 时播放键不亮。到 0 会自动确认当前歌。": "Play button is disabled above 85. Auto-confirms current song at 0.",
    "单人 / 对战 / 合作": "Solo / Versus / Co-op",
    "到 0 会自动选单人。": "Auto-selects Solo at 0.",
    "旅程 / 任务 / 对战": "Journey / Mission / Versus",
    "到 0 会自动进旅程。": "Auto-enters Journey at 0.",
    "音符和道具": "Notes & Items",
    "两步共用这一个倒计时。到 0 会自己进入下一步。": "Both steps share this timer. Auto-advances at 0.",
    "局内": "In-Game",
    "铺面结束仍会通关结算。": "Normal stage clear results still trigger when the chart ends.",
    "跳过教程视频": "Skip Tutorial Video",
    "对战、游客、新手旅程、离线开局不再播教程。": "Skips tutorial in Versus, Guest, Beginner Journey, and Offline startup.",
    "游戏结束自动返回主菜单兜底": "Auto-Return to Title Fallback",
    "20 秒未点或 4 秒卡死时强制回 Title（会改文件大小，需最后应用）。": (
        "Forces return to Title after 20s idle or 4s stuck (changes file size; apply last)."
    ),
    "解除高级与大师谱面游玩限制": "Unlock Hard & Master Charts",
    "高级无需先通关普通；大师无需通关高级或完成成就/任务。": "Hard no longer requires Normal clear; Master requires no prior clear or mission.",
    "已解除高级与大师谱面游玩限制": "Hard & Master chart restrictions removed",
    "高级与大师谱面游玩限制已还原": "Hard & Master chart restrictions reverted",
    "离线也能选歌": "Offline Song Select",
    "对战和找人仍要联网。": "Versus and matchmaking still require an internet connection.",
    "离线选歌限制已还原": "Offline song select restriction reverted",
    "解锁所有大师谱面": "Unlock All Master Charts",
    "星级小于 0 的难度仍然不出现。": "Difficulties with star rating < 0 still stay hidden.",
    "已解锁所有大师谱面": "All Master charts unlocked",
    "大师谱面列表过滤已还原": "Master chart list filter reverted",
    "音符全部解锁": "Unlock All Note Types",
    "红、绿、蓝、箭头都算已解锁。": "Red, green, blue, and arrow notes are all treated as unlocked.",
    "音符已全部解锁": "All note types unlocked",
    "音符解锁已还原": "Note type unlocks reverted",
    "道具保持 999": "Keep Items at 999",
    "这 18 个道具用掉也不减少，且解除游客/离线使用限制。": "All 18 items stay at 999 and guest/offline restrictions are removed.",
    "道具数量保持 999（已解除使用限制）": "Inventory items set to 999 (restrictions removed)",
    "道具数量与使用限制已还原": "Inventory items and restrictions reverted",
    "金币保持 99999": "Keep Coins at 99999",
    "消费金币不会减少。": "Coins stay at 99999 when spent.",
    "金币数量保持 99999": "Coins set to 99999",
    "金币数量已还原": "Coins reverted",
    "宝石保持 99999": "Keep Gems at 99999",
    "消费宝石不会减少。": "Gems stay at 99999 when spent.",
    "宝石数量保持 99999": "Gems set to 99999",
    "宝石数量已还原": "Gems reverted",
    "要填整数": "Must be a whole number",
    "要在 {low} 到 {high} 之间": "Must be between {low} and {high}",
    "{title} 的字节对不上，这一项没改": "Bytes for {title} do not match; skipped",
    "{title} 停在 {seconds} 秒": "{title} frozen at {seconds}s",
    "{title} 已还原": "{title} reverted",
    "局内倒计时的字节对不上，这一项没改": "Bytes for In-Game timer do not match; skipped",
    "局内倒计时停在 {seconds} 秒": "In-Game timer frozen at {seconds}s",
    "局内倒计时已还原": "In-Game timer reverted",
    "教程场景的字节对不上，这一项没改": "Bytes for Tutorial scene do not match; skipped",
    "教程视频已跳过": "Tutorial video skipped",
    "教程视频已还原": "Tutorial video reverted",
    "没有需要改的项": "No changes needed",
    "当前：原版": "Status: Original",
    "当前：已改": "Status: Patched",
    "当前：字节对不上，不会改": "Status: Bytes mismatch (locked)",
    "当前：倒计时开着": "Status: Timer active",
    "当前：已停在 {seconds} 秒": "Status: Frozen at {seconds}s",
    "当前：会播放教程": "Status: Tutorial enabled",
    "当前：已跳过教程": "Status: Tutorial skipped",
    "当前：已加返回兜底": "Status: Fallback patched",
    "当前：原版（未加兜底）": "Status: Original (no fallback)",
    "先点「浏览」，选择游戏根目录。": "Click Browse to select the game root folder first.",
    "请选择游戏根目录，不是单个文件。": "Select the game root folder, not a single file.",
    "这个目录里没有 Game\\TopStar2_Data\\Managed\\Assembly-CSharp.dll。\n请选游戏根目录。": (
        "Game\\TopStar2_Data\\Managed\\Assembly-CSharp.dll was not found in this folder.\n"
        "Please select the game root folder."
    ),
    "读不了这个文件。先退出游戏。\n{exc}": "Cannot read file. Exit the game first.\n{exc}",
    "「游戏结束自动返回主菜单兜底」修改了 DLL 结构，无法单独取消勾选。\n如需还原，请用同目录下的 Assembly-CSharp.dll.bak 覆盖 Assembly-CSharp.dll。": (
        "Auto-Return to Title Fallback modifies the DLL structure and cannot be unchecked alone.\n"
        "To revert, overwrite Assembly-CSharp.dll with Assembly-CSharp.dll.bak in the same folder."
    ),
    "当前 DLL 已写入「游戏结束自动返回主菜单兜底」，文件偏移已变化。\n如需调整其他项，请先用 Assembly-CSharp.dll.bak 还原后再重新勾选应用。": (
        "Auto-Return to Title Fallback is already applied, shifting file offsets.\n"
        "To change other options, restore Assembly-CSharp.dll.bak first and re-apply."
    ),
    "找不到 {path}": "Cannot find {path}",
    "TopStar2Patcher 返回 {code}": "TopStar2Patcher exited with code {code}",
    "游戏结束已加返回主菜单兜底": "Auto-Return to Title Fallback applied",
    "游戏结束返回主菜单兜底已还原": "Auto-Return to Title Fallback reverted",
    "去IO检测": "Bypass IO Check",
    "跳过开机 IO 板串口检测，F1/F2 可模拟测试/服务键。": "Skips startup IO board check; F1/F2 simulate Test/Service keys.",
    "已开启去IO检测": "IO check bypassed",
    "IO检测已还原": "IO check reverted",
    "免费投币": "Free Play",
    "强制开启免费游玩（Free Play），无需投币即可开始。": "Forces Free Play mode; start games without inserting coins.",
    "已开启免费投币": "Free Play enabled",
    "免费投币已还原": "Free Play reverted",
    "修复触屏与鼠标": "Fix Touch & Mouse",
    "禁用框体串口/原始触摸接管，启用 Unity 鼠标与触屏输入。": "Disables cabinet raw touch override and enables Unity mouse & touch input.",
    "已修复触屏与鼠标输入": "Touch & mouse input fixed",
    "触屏与鼠标输入已还原": "Touch & mouse input reverted",
    "检测到原版加密 DLL，正在自动解密（会短暂启动一次游戏进程）…": "Encrypted original DLL detected; decrypting via game process...",
    "自动解密失败：{exc}": "Auto-decryption failed: {exc}",
    "找不到 {exe}": "Cannot find {exe}",
    "未能在游戏进程内存中找到解密后的 Assembly-CSharp.dll": "Could not locate decrypted Assembly-CSharp.dll in game memory",
    "20 秒未点或 4 秒卡死时强制回 Title。": "Forces return to Title after 20s idle or 4s stuck.",
    "游戏结束自动返回主菜单兜底": "Auto-Return to Title Fallback",
    "写不进去。先退出游戏。\n{exc}": "Cannot write file. Exit the game first.\n{exc}",
    "已写入。重新启动游戏再生效。\n\n{notes}": "Changes written. Restart the game to take effect.\n\n{notes}",
    "高刷与高帧率": "High Refresh & FPS",
    "解锁 120/240Hz 刷新率与帧率限制，不影响游戏速度。": "Unlocks 120/240Hz display & FPS cap at original game speed.",
    "高刷与高帧率已设为 {fps}Hz / {fps}FPS": "Refresh rate & FPS set to {fps}Hz / {fps}FPS",
    "高刷与高帧率已还原": "Refresh rate & FPS reverted",
    "显示内置 FPS": "Show Built-in FPS",
    "在屏幕左上角显示游戏内置 FPS 计数器。": "Displays the game's built-in FPS counter at the top-left corner.",
    "已开启内置 FPS 显示": "Built-in FPS display enabled",
    "内置 FPS 显示已还原": "Built-in FPS display reverted",
    "功能分类": "CATEGORIES",
    "选歌与谱面": "Songs & Charts",
    "解除谱面难度与离线选歌限制": "Unlock chart difficulties and offline song selection",
    "物品与货币": "Items & Currency",
    "解锁全部音符皮肤并锁定道具与货币数量": "Unlock note skins and lock item, coin & gem counts",
    "倒计时控制": "Stage Timers",
    "自定义各界面与局内倒计时停驻秒数": "Freeze menu and in-game timers at custom seconds",
    "系统与高刷": "System & Display",
    "高刷帧率解锁、触屏修复、免投币与系统补丁": "120/240Hz unlock, touch fix, Free Play & system patches",
    "快捷操作": "QUICK ACTIONS",
    "全选本页": "Enable Page",
    "清空本页": "Disable Page",
    "应用修改": "Apply Changes",
    "已启用 {on} / {total} 项": "{on} / {total} Enabled",
    "未加载文件": "Not Loaded",
    "退出游戏后修改并点击「应用修改」生效 · 首次写入自动备份 .bak（不覆盖已有备份）": (
        "Exit game before applying · Automatically backs up .bak on first write (never overwrites)"
    ),
    "深色奢华": "Night Luxe",
    "浅色高贵": "Pearl Light",
    "切换至浅色高贵": "Pearl Light",
    "切换至深色奢华": "Night Luxe",
    "待载入游戏目录": "Awaiting Game Folder",
    "已就绪 · {on} / {total} 项启用": "Ready · {on} / {total} Active",
    "选择游戏根目录后点击「读取」，或直接将游戏目录拖拽至此窗口": (
        "Click Browse & Read, or drag and drop the game root folder anywhere into this window"
    ),
    "待读取游戏目录以同步补丁状态": "Load game folder to sync patch states",
    "已生效": "Active",
    "停驻 {seconds}s": "Hold {seconds}s",
    "流光旗舰补丁工具": "Flagship Edition",
    "旗舰高定版": "HAUTE EDITION",
    "午夜星河": "Midnight Luxe",
    "珍珠瓷白": "Haute Pearl",
    "难度解锁 · 离线选歌": "Chart & Offline Unlocks",
    "音符皮肤 · 道具货币": "Skins, Items & Currency",
    "界面与局内秒数停驻": "Menu & Stage Freeze",
    "高刷解锁 · 触控框体": "120/240Hz · Touch · IO",
    "关闭垂直同步": "Disable VSync",
    "强制关闭垂直同步（vSyncCount = 0），降低输入延迟。": "Forces QualitySettings.vSyncCount = 0 to reduce input latency.",
    "已强制关闭垂直同步": "VSync forced off",
    "垂直同步设置已还原": "VSync setting reverted",
    "高刷帧率解锁、垂直同步、触屏修复、免投币与系统补丁": "Refresh rate, VSync, touch fix, free play & system patches",
}


def _display_language_is_chinese() -> bool:
    try:
        lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except Exception:
        lang_id = 0
    if lang_id:
        return (lang_id & 0x3FF) == 0x04
    name = locale.getlocale()[0]
    if name and name.lower().replace("-", "_").startswith("zh"):
        return True
    return False


chinese = _display_language_is_chinese()


def is_chinese() -> bool:
    return chinese


def set_chinese(value: bool) -> None:
    global chinese
    chinese = bool(value)


def toggle_language() -> bool:
    global chinese
    chinese = not chinese
    return chinese


def t(text: str, **kwargs) -> str:
    if not chinese:
        text = _EN.get(text, text)
    if kwargs:
        return text.format(**kwargs)
    return text
