import gc
import json
import os
import re
import sys
import time
import struct
import platform
import shutil
import subprocess
import threading
import urllib.request
import uuid
import zipfile
import customtkinter as ctk
import minecraft_launcher_lib
import requests
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk


def trim_memory():
    """Принудительно сбрасывает кэши и снижает потребление RAM процесса до минимума."""
    try:
        gc.collect()
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.kernel32.SetProcessWorkingSetSize(ctypes.windll.kernel32.GetCurrentProcess(), -1, -1)
    except Exception:
        pass


WHITELIST_MOD_KEYWORDS = [
    'replaymod', 'replay-mod', 'flashback', 'sodium', 'lithium', 'ferritecore',
    'entityculling', 'immediatelyfast', 'fabric-api', 'fabricloader', 'modmenu',
    'iris', 'indium', 'appleskin', 'cloth-config', 'yacl'
]

FUNTIME_FORBIDDEN_KEYWORDS = [
    'xray', 'freecam', 'baritone', 'tweakeroo', 'autofish', 'automining', 'replantingcrops',
    'autoharvest', 'reap', 'accurateblockplacement', 'playerspotlight', 'player_spotlight',
    'auchelper', 'auc_helper', 'chesttracker', 'chest_tracker', 'friendhighlighter',
    'donutauction', 'diamondgen', 'basefinder', 'truesight', 'neat', 'chunkanimator',
    'mobhealthbar', 'litematica', 'schematica', 'block-entity-tooltip', 'worldedit',
    'betterpvp', 'better_pvp', 'worlddownloader', 'removeblindness', 'entityoutline',
    'antiinvis', 'cooldownshud', 'usetracker', 'cheatutils', 'nodarkness', 'removewarden',
    'funtime-ah-helper', 'funtime_ah_helper', 'ftutils', 'autobuy', 'autosell',
    'autocasino', 'autopilot', 'inventorycontroltweaks', 'autoleave', 'foodslot',
    'quickstack', 'itemswap', 'autotool', 'movementingui', 'fasterblockplacement',
    'fireworkhelper', 'effortlessbuilding', 'invmove', 'inventoryprofilesnext',
    'autojumpreset', 'dontheatteammates', 'donthitteammates', 'cleancut', 'autoattack',
    'autoaim', 'fevervisuals', 'luminarvisuals', 'ascart', 'simplevisuals',
    'wavevisuals', 'clientcommands', 'wurst', 'meteor', 'aristois', 'liquidbounce',
    'thunderhack', 'impact', 'inertia', 'sigma', 'bleachhack', 'future', 'rusherhack',
    'boze', 'kura', 'nursultan', 'celestial', 'expensive', 'akrien', 'wild', 'delta',
    'minced', 'vape', 'doomsday', 'releon', 'deadcode', 'zamorozka', 'matrix', 'dd'
]


def scan_forbidden_mods(mc_dir):
    """Сканирует только директории клиента ThunderDLC на наличие запрещенных читов и модификаций."""
    mods_dirs = [os.path.join(mc_dir, "mods")]
    parent_mc = os.path.dirname(os.path.dirname(mc_dir))
    if parent_mc and os.path.isdir(os.path.join(parent_mc, "mods")) and os.path.join(parent_mc, "mods") not in mods_dirs:
        mods_dirs.append(os.path.join(parent_mc, "mods"))
    
    root_dlc = r"C:\ThunderDLC"
    if os.path.isdir(os.path.join(root_dlc, "mods")) and os.path.join(root_dlc, "mods") not in mods_dirs:
        mods_dirs.append(os.path.join(root_dlc, "mods"))

    forbidden_found = []
    seen_files = set()

    # 1. Проверка папок версий на наличие чит-клиентов
    versions_dir = os.path.join(mc_dir, "versions")
    if not os.path.exists(versions_dir) and parent_mc:
        versions_dir = os.path.join(parent_mc, "versions")
    if os.path.exists(versions_dir):
        for v in os.listdir(versions_dir):
            v_low = v.lower()
            for kw in ['celestial', 'expensive', 'nursultan', 'doomsday', 'cortex', 'mhub', 'releon', 'meteor', 'thunderhack', 'wurst', 'deadcode', 'akrien', 'zamorozka']:
                if kw in v_low:
                    forbidden_found.append(f"Клиент: {v}")
                    break

    # 2. Сканирование jar файлов в папке mods
    for m_dir in mods_dirs:
        if not os.path.exists(m_dir):
            continue
        for f in os.listdir(m_dir):
            if f in seen_files or (not f.endswith(".jar") and not f.endswith(".jar.disabled")):
                continue
            seen_files.add(f)
            full_p = os.path.join(m_dir, f)
            clean_name = f.lower()

            # Белый список разрешенных модификаций
            is_whitelisted = False
            for w in WHITELIST_MOD_KEYWORDS:
                if w in clean_name:
                    is_whitelisted = True
                    break
            if is_whitelisted:
                continue

            # Проверка SoupApi (запрещен только строго ниже версии 3.0.0)
            if "soupapi" in clean_name:
                m_ver = re.search(r"soupapi.*?(\d+)(?:\.(\d+))?", clean_name)
                if m_ver:
                    try:
                        major = int(m_ver.group(1))
                        if major >= 3:
                            continue  # Версии 3.0.0 и выше РАЗРЕШЕНЫ
                    except Exception:
                        pass

            # Проверка по ключевым словам в имени файла
            matched = False
            for kw in FUNTIME_FORBIDDEN_KEYWORDS:
                if kw.replace('_', '').replace('-', '') in clean_name.replace('-', '').replace('_', '').replace(' ', ''):
                    forbidden_found.append(f)
                    matched = True
                    break

            # Глубокая проверка метаданных fabric.mod.json и пакетов внутри JAR
            if not matched and f.endswith(".jar"):
                try:
                    with zipfile.ZipFile(full_p, 'r') as z:
                        namelist = z.namelist()
                        # Проверка fabric.mod.json
                        if 'fabric.mod.json' in namelist:
                            m_data = json.loads(z.read('fabric.mod.json').decode('utf-8', errors='ignore'))
                            m_id = m_data.get('id', '').lower().replace('-', '').replace('_', '')
                            m_name = m_data.get('name', '').lower().replace('-', '').replace('_', '').replace(' ', '')
                            for kw in FUNTIME_FORBIDDEN_KEYWORDS:
                                ckw = kw.replace('_', '').replace('-', '')
                                if ckw in m_id or ckw in m_name:
                                    forbidden_found.append(f"{m_data.get('name', f)} ({f})")
                                    matched = True
                                    break

                        # Проверка сигнатур внутренних пакетов классов
                        if not matched:
                            for entry in namelist:
                                entry_low = entry.lower()
                                for kw in ['cortex', 'mhub', 'doomsday', 'expensive', 'celestial', 'nursultan', 'thunderhack', 'meteorclient', 'baritone', 'wurst', 'liquidbounce']:
                                    if kw in entry_low:
                                        forbidden_found.append(f)
                                        matched = True
                                        break
                                if matched:
                                    break
                except Exception:
                    pass
    return forbidden_found


class FakeBanWindow(ctk.CTkToplevel):
    def __init__(self, server_host, nick, forbidden_mods, mc_dir):
        super().__init__()
        self.server_host = server_host
        self.nick = nick
        self.forbidden_mods = forbidden_mods
        self.mc_dir = mc_dir
        self.mods_dir = os.path.join(mc_dir, "mods")

        self.title("FunTime Security System // Console Auto-Ban")
        self.geometry("640x520")
        self.resizable(False, False)
        self.configure(fg_color="#0d0404")
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 640) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.focus_force()

        def _beep():
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

        self.stage1_frame = ctk.CTkFrame(self, fg_color="#180808", border_color="#8B0000", border_width=2, corner_radius=12)
        self.stage1_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            self.stage1_frame,
            text="⛔ ВЫ ЗАБЛОКИРОВАНЫ НА СЕРВЕРЕ FUNTIME",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FF2222"
        ).pack(pady=(18, 10))

        info_box = ctk.CTkFrame(self.stage1_frame, fg_color="#0e0404", border_color="#441111", border_width=1, corner_radius=8)
        info_box.pack(fill="x", padx=20, pady=10)

        import random
        ban_id = random.randint(100000, 999999)
        bad_mods_text = "\n".join([f"  • {m}" for m in forbidden_mods[:5]])

        ban_info = (
            f"Игровой никнейм: {nick}\n"
            f"Сервер: {server_host}\n"
            f"Причина: 4.3 (Хранение / Использование запрещенных модификаций)\n"
            f"Заблокировал: FunTime Console [Auto-Ban Engine]\n"
            f"Срок бана: НАВСЕГДА (PERMANENT)\n"
            f"ID инцидента: #FT-{ban_id}\n\n"
            f"Обнаружен запрещенный софт в игре:\n{bad_mods_text}"
        )
        ctk.CTkLabel(
            info_box,
            text=ban_info,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#EEEEEE",
            justify="left"
        ).pack(anchor="w", padx=15, pady=12)

        self.countdown_val = 5
        self.timer_label = ctk.CTkLabel(
            self.stage1_frame,
            text=f"Апелляция отклонена. Данные передаются администрации... ({self.countdown_val})",
            font=ctk.CTkFont(size=12),
            text_color="#FF6666"
        )
        self.timer_label.pack(pady=(10, 5))

        self._tick_countdown()

    def _tick_countdown(self):
        if self.countdown_val > 1:
            self.countdown_val -= 1
            self.timer_label.configure(text=f"Апелляция отклонена. Данные передаются администрации... ({self.countdown_val})")
            self.after(1000, self._tick_countdown)
        else:
            self._reveal_prank()

    def _reveal_prank(self):
        for widget in self.stage1_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.stage1_frame,
            text="⚡ ТЫ ЗАБАНЕН БЛЯТЬ! ХАХАХАХ",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#FFCC00"
        ).pack(pady=(18, 10))

        safe_box = ctk.CTkFrame(self.stage1_frame, fg_color="#141414", border_color="#333333", border_width=1, corner_radius=8)
        safe_box.pack(fill="x", padx=20, pady=10)

        bad_mods_text = "\n".join([f"  • {m}" for m in self.forbidden_mods])
        safe_info = (
            "Мы вовремя перехватили твой вход на FunTime и спасли от РЕАЛЬНОГО БАНА!\n\n"
            "По правилам forum.funtime.su/modifications за следующие моды тебя бы сразу снесли:\n"
            f"{bad_mods_text}\n\n"
            "Удали или отключи эти моды из папки .minecraft/mods перед тем как заходить на FunTime!"
        )
        ctk.CTkLabel(
            safe_box,
            text=safe_info,
            font=ctk.CTkFont(size=12),
            text_color="#DDDDDD",
            justify="left"
        ).pack(anchor="w", padx=15, pady=12)

        btn_row = ctk.CTkFrame(self.stage1_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            btn_row,
            text="📁 Открыть папку mods",
            width=200,
            height=38,
            fg_color="#2b2b2b",
            hover_color="#3c3c3c",
            command=self._open_mods_folder
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="🚀 Понял, спасибо за сейв!",
            width=200,
            height=38,
            fg_color="#0066cc",
            hover_color="#0052a3",
            command=self.destroy
        ).pack(side="right")

    def _open_mods_folder(self):
        try:
            if os.path.exists(self.mods_dir):
                os.startfile(self.mods_dir)
            elif os.path.exists(self.mc_dir):
                os.startfile(self.mc_dir)
        except Exception:
            pass

# ========== КОНФИГ ==========
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "launcher_version": "1.1.0",
    "default_nick": "",
    "selected_version": "ThunderClient 1.21.11",
    "discord_client_id": "1544251893281202246",
    "ram": "4G",
    "minecraft_dir": "./.minecraft",
    "discord_invite": "https://discord.gg/ТВОЙ_СЕРВЕР",
    "vk_group": "https://vk.me/join/Vwe_cQ/FHhqZp_abcYo1GoDYOPzQ1GpMlsU=",
    "fullscreen": False,
    "keep_open": False,
    "width": 854,
    "height": 480,
    "jvm_args": "",
    "versions": [
        {
            "name": "1.21.4",
            "display_name": "ThunderClient 1.21.4",
            "type": "fabric",
            "fabric_version": "0.19.3",
            "mc_subdir": "1.21.4",
            "mods": [
                {
                    "name": "fabric-api-0.119.4+1.21.4.jar",
                    "url": "https://cdn.modrinth.com/data/P7dR8mSH/versions/p96k10UR/fabric-api-0.119.4%2B1.21.4.jar",
                    "path": "mods/fabric-api-0.119.4+1.21.4.jar"
                },
                {
                    "name": "sodium-fabric-0.6.13+mc1.21.4.jar",
                    "url": "https://cdn.modrinth.com/data/AANobbMI/versions/c3YkZvne/sodium-fabric-0.6.13%2Bmc1.21.4.jar",
                    "path": "mods/sodium-fabric-0.6.13+mc1.21.4.jar"
                },
                {
                    "name": "lithium-fabric-0.15.3+mc1.21.4.jar",
                    "url": "https://cdn.modrinth.com/data/gvQqBUqZ/versions/u8pHPXJl/lithium-fabric-0.15.3%2Bmc1.21.4.jar",
                    "path": "mods/lithium-fabric-0.15.3+mc1.21.4.jar"
                },
                {
                    "name": "ferritecore-7.1.3-fabric.jar",
                    "url": "https://cdn.modrinth.com/data/uXXizFIs/versions/7KqeXPRS/ferritecore-7.1.3-fabric.jar",
                    "path": "mods/ferritecore-7.1.3-fabric.jar"
                },
                {
                    "name": "entityculling-fabric-1.10.5-mc1.21.4.jar",
                    "url": "https://cdn.modrinth.com/data/NNAgCjsB/versions/O31j1KhT/entityculling-fabric-1.10.5-mc1.21.4.jar",
                    "path": "mods/entityculling-fabric-1.10.5-mc1.21.4.jar"
                },
                {
                    "name": "ImmediatelyFast-Fabric-1.8.7+1.21.4.jar",
                    "url": "https://cdn.modrinth.com/data/5ZwdcRci/versions/gF6yVXr9/ImmediatelyFast-Fabric-1.8.7%2B1.21.4.jar",
                    "path": "mods/ImmediatelyFast-Fabric-1.8.7+1.21.4.jar"
                }
            ]
        },
        {
            "name": "1.21.11",
            "display_name": "ThunderClient 1.21.11",
            "type": "fabric",
            "fabric_version": "0.19.3",
            "mc_subdir": "1.21.11",
            "mods": [
                {
                    "name": "fabric-api-0.141.5+1.21.11.jar",
                    "url": "https://cdn.modrinth.com/data/P7dR8mSH/versions/zGF3drOQ/fabric-api-0.141.5%2B1.21.11.jar",
                    "path": "mods/fabric-api-0.141.5+1.21.11.jar"
                },
                {
                    "name": "sodium-fabric-0.8.14+mc1.21.11.jar",
                    "url": "https://cdn.modrinth.com/data/AANobbMI/versions/rkdTcxoT/sodium-fabric-0.8.14%2Bmc1.21.11.jar",
                    "path": "mods/sodium-fabric-0.8.14+mc1.21.11.jar"
                },
                {
                    "name": "lithium-fabric-0.21.4+mc1.21.11.jar",
                    "url": "https://cdn.modrinth.com/data/gvQqBUqZ/versions/Ow7wA0kG/lithium-fabric-0.21.4%2Bmc1.21.11.jar",
                    "path": "mods/lithium-fabric-0.21.4+mc1.21.11.jar"
                },
                {
                    "name": "ferritecore-8.2.0-fabric.jar",
                    "url": "https://cdn.modrinth.com/data/uXXizFIs/versions/Ii0gP3D8/ferritecore-8.2.0-fabric.jar",
                    "path": "mods/ferritecore-8.2.0-fabric.jar"
                },
                {
                    "name": "entityculling-fabric-1.10.5-mc1.21.11.jar",
                    "url": "https://cdn.modrinth.com/data/NNAgCjsB/versions/sP0vNbeN/entityculling-fabric-1.10.5-mc1.21.11.jar",
                    "path": "mods/entityculling-fabric-1.10.5-mc1.21.11.jar"
                },
                {
                    "name": "ImmediatelyFast-Fabric-1.14.3+1.21.11.jar",
                    "url": "https://cdn.modrinth.com/data/5ZwdcRci/versions/4EwhsTu7/ImmediatelyFast-Fabric-1.14.3%2B1.21.11.jar",
                    "path": "mods/ImmediatelyFast-Fabric-1.14.3+1.21.11.jar"
                }
            ]
        },
        {
            "name": "1.20.2",
            "display_name": "ThunderClient 1.20.2",
            "type": "fabric",
            "fabric_version": "0.19.3",
            "mc_subdir": "1.20.2",
            "mods": [
                {
                    "name": "fabric-api-0.91.6+1.20.2.jar",
                    "url": "https://cdn.modrinth.com/data/P7dR8mSH/versions/8GVp7wDk/fabric-api-0.91.6%2B1.20.2.jar",
                    "path": "mods/fabric-api-0.91.6+1.20.2.jar"
                },
                {
                    "name": "sodium-fabric-mc1.20.2-0.5.5.jar",
                    "url": "https://cdn.modrinth.com/data/AANobbMI/versions/pmgeU5yX/sodium-fabric-mc1.20.2-0.5.5.jar",
                    "path": "mods/sodium-fabric-mc1.20.2-0.5.5.jar"
                },
                {
                    "name": "lithium-fabric-mc1.20.2-0.12.0.jar",
                    "url": "https://cdn.modrinth.com/data/gvQqBUqZ/versions/qdzL5Hkg/lithium-fabric-mc1.20.2-0.12.0.jar",
                    "path": "mods/lithium-fabric-mc1.20.2-0.12.0.jar"
                },
                {
                    "name": "ferritecore-6.0.1-fabric.jar",
                    "url": "https://cdn.modrinth.com/data/uXXizFIs/versions/unerR5MN/ferritecore-6.0.1-fabric.jar",
                    "path": "mods/ferritecore-6.0.1-fabric.jar"
                },
                {
                    "name": "entityculling-fabric-1.10.5-mc1.20.2.jar",
                    "url": "https://cdn.modrinth.com/data/NNAgCjsB/versions/hrf9TtVy/entityculling-fabric-1.10.5-mc1.20.2.jar",
                    "path": "mods/entityculling-fabric-1.10.5-mc1.20.2.jar"
                },
                {
                    "name": "ImmediatelyFast-Fabric-1.5.5+1.20.4.jar",
                    "url": "https://cdn.modrinth.com/data/5ZwdcRci/versions/iwYUrQJO/ImmediatelyFast-Fabric-1.5.5%2B1.20.4.jar",
                    "path": "mods/ImmediatelyFast-Fabric-1.5.5+1.20.4.jar"
                }
            ]
        },
        {
            "name": "1.16.5",
            "display_name": "ThunderClient 1.16.5",
            "type": "fabric",
            "fabric_version": "0.19.5",
            "mc_subdir": "1.16.5",
            "mods": [
                {
                    "name": "fabric-api-0.42.0+1.16.jar",
                    "url": "https://cdn.modrinth.com/data/P7dR8mSH/versions/0.42.0%2B1.16/fabric-api-0.42.0%2B1.16.jar",
                    "path": "mods/fabric-api-0.42.0+1.16.jar"
                },
                {
                    "name": "sodium-fabric-mc1.16.5-0.2.0+build.4.jar",
                    "url": "https://cdn.modrinth.com/data/AANobbMI/versions/mc1.16.5-0.2.0/sodium-fabric-mc1.16.5-0.2.0%2Bbuild.4.jar",
                    "path": "mods/sodium-fabric-mc1.16.5-0.2.0+build.4.jar"
                },
                {
                    "name": "lithium-fabric-mc1.16.5-0.6.6.jar",
                    "url": "https://cdn.modrinth.com/data/gvQqBUqZ/versions/mc1.16.5-0.6.6/lithium-fabric-mc1.16.5-0.6.6.jar",
                    "path": "mods/lithium-fabric-mc1.16.5-0.6.6.jar"
                },
                {
                    "name": "ferritecore-2.1.1-fabric.jar",
                    "url": "https://cdn.modrinth.com/data/uXXizFIs/versions/3UkWIj4a/ferritecore-2.1.1-fabric.jar",
                    "path": "mods/ferritecore-2.1.1-fabric.jar"
                },
                {
                    "name": "entityculling-fabric-mc1.16.5-1.5.2.jar",
                    "url": "https://cdn.modrinth.com/data/NNAgCjsB/versions/1.5.2-fabric-1.16/entityculling-fabric-mc1.16.5-1.5.2.jar",
                    "path": "mods/entityculling-fabric-mc1.16.5-1.5.2.jar"
                }
            ]
        }
    ]
}

# ========== КОНСТАНТЫ И СТИЛИ ==========
WIDTH, HEIGHT = 900, 550
LEFT_W = 360
RIGHT_X = LEFT_W + 44
FIELD_W = 456

COL_ACCENT = (230, 230, 230)
RIGHT_PANEL_COLOR = "#121212"
DIVIDER_COLOR = "#222222"
INPUT_COLOR = "#1a1a1a"
INPUT_BORDER = "#333333"
BTN_COLOR = "#2b2b2b"
BTN_HOVER = "#3c3c3c"
BTN_KILL_COLOR = "#8B0000"
BTN_KILL_HOVER = "#A50000"

_font_cache = {}
FONT_BOLD_CANDIDATES = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica-Bold.ttf"]
FONT_REGULAR_CANDIDATES = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Helvetica.ttf"]


def load_font(candidates, size):
    key = (tuple(candidates), size)
    if key in _font_cache:
        return _font_cache[key]
    font = None
    for name in candidates:
        try:
            font = ImageFont.truetype(name, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def make_text_sprite(text, font, color=(255, 255, 255, 255), align="center", spacing=6):
    tmp = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    bbox = tmp_draw.multiline_textbbox((0, 0), text, font=font, align=align, spacing=spacing)
    w = int(bbox[2] - bbox[0]) + 4
    h = int(bbox[3] - bbox[1]) + 4

    sprite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    draw.multiline_text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=color, align=align, spacing=spacing)
    return sprite


def make_logo_sprite(size=112, color=COL_ACCENT):
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = big / 2
    r = big * 0.40

    diamond = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)]
    draw.line(diamond + [diamond[0]], fill=(*color, 255), width=int(3 * scale), joint="curve")

    bolt = [
        (c + big * 0.06, c - big * 0.22),
        (c - big * 0.12, c + big * 0.03),
        (c - big * 0.01, c + big * 0.03),
        (c - big * 0.08, c + big * 0.24),
        (c + big * 0.15, c - big * 0.03),
        (c + big * 0.02, c - big * 0.03),
    ]
    draw.polygon(bolt, fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def get_app_resource(filename):
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    p = os.path.join(base_dir, filename)
    if os.path.exists(p):
        return p
    p2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(p2):
        return p2
    return None


def make_app_icon(size=64):
    for name in ["icon.png", "icon.ico"]:
        p = get_app_resource(name)
        if p and os.path.exists(p):
            try:
                return Image.open(p).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            except Exception:
                pass
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def apply_default_mc_options(minecraft_dir):
    options_path = os.path.join(minecraft_dir, "options.txt")
    target_settings = {
        "lang": "ru_ru",
        "narrator": "0",
        "tutorialStep": "none",
        "onboardAccessibility": "false"
    }

    existing_settings = {}
    if os.path.exists(options_path):
        try:
            with open(options_path, "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.strip().split(":", 1)
                        existing_settings[k] = v
        except Exception:
            pass

    for k, v in target_settings.items():
        existing_settings[k] = v

    try:
        with open(options_path, "w", encoding="utf-8") as f:
            for k, v in existing_settings.items():
                f.write(f"{k}:{v}\n")
    except Exception as e:
        print(f"Ошибка сохранения options.txt: {e}")


def patch_exe_description(exe_path, new_name="ThunderDLC"):
    if platform.system() != "Windows":
        return
    try:
        import win32api
        import win32con
    except ImportError:
        return
    try:
        with open(exe_path, "rb") as f:
            data = f.read()

        target = "OpenJDK Platform binary".encode("utf-16le")
        replacement = new_name.ljust(len("OpenJDK Platform binary")).encode("utf-16le")

        if target in data:
            new_data = data.replace(target, replacement)
            with open(exe_path, "wb") as f:
                f.write(new_data)
    except Exception as e:
        print(f"Не удалось пропатчить ресурсы exe: {e}")


class DynamicBackground:
    def __init__(self, window, width, height):
        self.window = window
        self.width = width
        self.height = height
        self.frames = []
        self.frame_index = 0
        self.anim_job = None

        # 1. Приоритет: статичные фоны
        static_candidates = ["bg_menu.png", "bg_menu.jpg", "bg_menu.jpeg", "bg.png", "bg.jpg"]
        chosen_static = None
        for cand in static_candidates:
            p = get_app_resource(cand)
            if p:
                chosen_static = p
                break

        # 2. Если статичного нет, проверяем gif
        chosen_gif = None
        if not chosen_static:
            gif_candidates = ["bg_menu.gif", "bg.gif"]
            for cand in gif_candidates:
                p = get_app_resource(cand)
                if p:
                    chosen_gif = p
                    break

        logo_sprite = make_logo_sprite(112)
        lx, ly = width / 2, height * 0.40

        font_title = load_font(FONT_BOLD_CANDIDATES, 21)
        font_tag = load_font(FONT_REGULAR_CANDIDATES, 12)
        brand_title_sprite = make_text_sprite("ThunderDLC", font_title, (240, 240, 240, 255))
        brand_tagline_sprite = make_text_sprite(
            "Быстрый запуск, стабильные сборки —\nвсё уже внутри.",
            font_tag,
            (160, 160, 160, 255),
        )
        brand_text_y = height * 0.40 + 62
        brand_tag_y = height * 0.40 + 98

        def process_frame(img_pil):
            base = img_pil.convert("RGBA").resize((width, height), Image.LANCZOS)
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 120))
            frame = Image.alpha_composite(base, overlay)
            frame.paste(logo_sprite, (int(lx - 56), int(ly - 56)), logo_sprite)
            frame.paste(brand_title_sprite, (int(width / 2 - brand_title_sprite.width / 2), int(brand_text_y - brand_title_sprite.height / 2)), brand_title_sprite)
            frame.paste(brand_tagline_sprite, (int(width / 2 - brand_tagline_sprite.width / 2), int(brand_tag_y - brand_tagline_sprite.height / 2)), brand_tagline_sprite)
            return ImageTk.PhotoImage(frame)

        if chosen_static:
            try:
                base_img = Image.open(chosen_static)
                self.frames = [process_frame(base_img)]
            except Exception:
                self.frames = [process_frame(Image.new("RGBA", (width, height), (15, 15, 15, 255)))]
        elif chosen_gif:
            try:
                gif = Image.open(chosen_gif)
                frame_count = getattr(gif, "n_frames", 1)
                for f_idx in range(frame_count):
                    gif.seek(f_idx)
                    self.frames.append(process_frame(gif))
            except Exception:
                self.frames = [process_frame(Image.new("RGBA", (width, height), (15, 15, 15, 255)))]
        else:
            self.frames = [process_frame(Image.new("RGBA", (width, height), (15, 15, 15, 255)))]

        self.label = tk.Label(window, image=self.frames[0], bd=0, highlightthickness=0)
        self.label.place(x=0, y=0, width=width, height=height)
        self.label.lower()

        if len(self.frames) > 1:
            self._animate()

    def _animate(self):
        if not self.frames:
            return
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.label.configure(image=self.frames[self.frame_index])
        self.anim_job = self.window.after(50, self._animate)


class ModsManager:
    @staticmethod
    def download_mod(mod_info, minecraft_dir, progress_cb=None):
        url = mod_info.get("url")
        if not url:
            return None

        rel_path = mod_info.get("path")
        if rel_path:
            full_path = os.path.join(minecraft_dir, rel_path)
        else:
            filename = mod_info.get("name", url.split("/")[-1].split("?")[0])
            full_path = os.path.join(minecraft_dir, "mods", filename)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if os.path.exists(full_path):
            return full_path

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 8192
                with open(full_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total > 0:
                            progress_cb(downloaded, total)
        except Exception as e:
            print(f"Ошибка скачивания мода ({url}): {e}")
        return full_path

    @staticmethod
    def download_all(mods, minecraft_dir, progress_cb=None):
        if not mods:
            return
        total_mods = len(mods)
        for idx, mod in enumerate(mods):
            def mod_prog(current, total):
                if progress_cb and total > 0:
                    sub_prog = current / total
                    overall = (idx + sub_prog) / total_mods
                    progress_cb(overall, f"Загрузка модов ({idx + 1}/{total_mods}): {int(sub_prog * 100)}%")


# ========== DISCORD RICH PRESENCE ==========
class DiscordRPC:
    def __init__(self, client_id="1544251893281202246"):
        self.client_id = client_id
        self.pipe = None
        self.connected = False
        self.start_time = int(time.time())
        self.lock = threading.Lock()

    def connect(self):
        with self.lock:
            if self.connected and self.pipe:
                return True
            for i in range(10):
                pipe_name = rf"\\.\pipe\discord-ipc-{i}"
                try:
                    self.pipe = open(pipe_name, "r+b", buffering=0)
                    handshake = json.dumps({"v": 1, "client_id": str(self.client_id)})
                    msg = struct.pack("<II", 0, len(handshake)) + handshake.encode("utf-8")
                    self.pipe.write(msg)
                    resp_header = self.pipe.read(8)
                    if len(resp_header) == 8:
                        op, length = struct.unpack("<II", resp_header)
                        resp = json.loads(self.pipe.read(length).decode("utf-8", errors="ignore"))
                        if resp.get("evt") == "READY":
                            self.connected = True
                            return True
                    self.pipe.close()
                except Exception:
                    pass
            self.connected = False
            return False

    def update_presence(self, details=None, state=None, large_image="https://cdn.discordapp.com/app-icons/1544251893281202246/0672666f7c2422f9c0421133e0bb0184.png", large_text="ThunderDLC Client", small_image=None, small_text=None, buttons=None, start_time=None):
        if not self.connected:
            if not self.connect():
                return
        with self.lock:
            try:
                activity = {
                    "details": str(details)[:128] if details else None,
                    "state": str(state)[:128] if state else None,
                    "timestamps": {"start": int(start_time or self.start_time)},
                    "assets": {
                        "large_image": large_image or "app_icon",
                        "large_text": str(large_text)[:128] if large_text else "ThunderDLC Client"
                    }
                }
                if small_image:
                    activity["assets"]["small_image"] = small_image
                    if small_text:
                        activity["assets"]["small_text"] = str(small_text)[:128]

                if buttons:
                    valid_buttons = []
                    for b in buttons[:2]:
                        if isinstance(b, dict) and b.get("label") and b.get("url") and b["url"].startswith("http"):
                            valid_buttons.append({"label": str(b["label"])[:32], "url": b["url"]})
                    if valid_buttons:
                        activity["buttons"] = valid_buttons

                payload = json.dumps({
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": os.getpid(),
                        "activity": activity
                    },
                    "nonce": str(uuid.uuid4())
                })
                msg = struct.pack("<II", 1, len(payload)) + payload.encode("utf-8")
                self.pipe.write(msg)
                resp_header = self.pipe.read(8)
                if len(resp_header) == 8:
                    op, length = struct.unpack("<II", resp_header)
                    self.pipe.read(length)
            except Exception:
                self.connected = False
                try:
                    if self.pipe:
                        self.pipe.close()
                except Exception:
                    pass

    def close(self):
        with self.lock:
            self.connected = False
            if self.pipe:
                try:
                    self.pipe.close()
                except Exception:
                    pass
                self.pipe = None


# ========== НАСТРОЙКИ ==========
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, save_callback):
        super().__init__(parent)
        self.title("Настройки клиента")
        
        # Центрирование окна настроек на экране
        width, height = 520, 610
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.configure(fg_color="#141414")
        self.config = config
        self.save_callback = save_callback

        self.grab_set()

        ctk.CTkLabel(self, text="⚙  Настройки", font=ctk.CTkFont(size=20, weight="bold"), text_color="#FFFFFF").pack(anchor="w", padx=25, pady=(20, 15))

        ram_str = str(self.config.get("ram", "4G")).upper().replace("G", "")
        try:
            initial_ram = float(ram_str)
        except ValueError:
            initial_ram = 4.0

        ram_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        ram_frame.pack(fill="x", padx=25, pady=8)

        self.ram_val_label = ctk.CTkLabel(ram_frame, text=f"Выделение ОЗУ: {int(initial_ram)} GB", font=ctk.CTkFont(size=13, weight="bold"), text_color="#EEEEEE")
        self.ram_val_label.pack(anchor="w", padx=15, pady=(12, 5))

        self.ram_slider = ctk.CTkSlider(
            ram_frame,
            from_=2,
            to=16,
            number_of_steps=14,
            command=self._on_ram_slider_change,
            button_color="#4A4A4A",
            button_hover_color="#666666",
            progress_color="#3A3A3A"
        )
        self.ram_slider.set(initial_ram)
        self.ram_slider.pack(fill="x", padx=15, pady=(0, 15))

        path_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        path_frame.pack(fill="x", padx=25, pady=8)

        ctk.CTkLabel(path_frame, text="Директория Minecraft:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#EEEEEE").pack(anchor="w", padx=15, pady=(10, 5))
        p_sub = ctk.CTkFrame(path_frame, fg_color="transparent")
        p_sub.pack(fill="x", padx=15, pady=(0, 12))

        self.path_entry = ctk.CTkEntry(p_sub, fg_color="#121212", border_color="#333333", text_color="#FFFFFF", corner_radius=8)
        self.path_entry.insert(0, self.config.get("minecraft_dir", "./.minecraft"))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(p_sub, text="Обзор", width=80, fg_color="#2b2b2b", hover_color="#3c3c3c", corner_radius=8, command=self._browse_path).pack(side="right")

        jvm_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        jvm_frame.pack(fill="x", padx=25, pady=8)

        ctk.CTkLabel(jvm_frame, text="Дополнительные аргументы Java (JVM):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#EEEEEE").pack(anchor="w", padx=15, pady=(10, 5))
        self.jvm_entry = ctk.CTkEntry(jvm_frame, placeholder_text="Опционально (напр. -Dmyflag=1)", fg_color="#121212", border_color="#333333", text_color="#FFFFFF", corner_radius=8)
        self.jvm_entry.insert(0, self.config.get("jvm_args", ""))
        self.jvm_entry.pack(fill="x", padx=15, pady=(0, 12))

        res_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        res_frame.pack(fill="x", padx=25, pady=8)

        self.fullscreen_var = ctk.BooleanVar(value=self.config.get("fullscreen", False))
        self.fullscreen_check = ctk.CTkCheckBox(res_frame, text="Полноэкранный режим", variable=self.fullscreen_var, text_color="#EEEEEE")
        self.fullscreen_check.pack(anchor="w", padx=15, pady=(10, 5))

        self.keep_open_var = ctk.BooleanVar(value=self.config.get("keep_open", False))
        self.keep_open_check = ctk.CTkCheckBox(res_frame, text="Не закрывать лаунчер при запуске", variable=self.keep_open_var, text_color="#EEEEEE")
        self.keep_open_check.pack(anchor="w", padx=15, pady=(5, 10))

        r_sub = ctk.CTkFrame(res_frame, fg_color="transparent")
        r_sub.pack(anchor="w", padx=15, pady=(0, 12))

        ctk.CTkLabel(r_sub, text="Разрешение:", text_color="#AAAAAA").pack(side="left", padx=(0, 10))
        self.width_entry = ctk.CTkEntry(r_sub, width=70, fg_color="#121212", border_color="#333333", corner_radius=6)
        self.width_entry.insert(0, str(self.config.get("width", 854)))
        self.width_entry.pack(side="left")

        ctk.CTkLabel(r_sub, text="x", text_color="#888888").pack(side="left", padx=5)

        self.height_entry = ctk.CTkEntry(r_sub, width=70, fg_color="#121212", border_color="#333333", corner_radius=6)
        self.height_entry.insert(0, str(self.config.get("height", 480)))
        self.height_entry.pack(side="left")

        ctk.CTkButton(self, text="Сохранить настройки", height=42, fg_color="#2b2b2b", hover_color="#3c3c3c", font=ctk.CTkFont(weight="bold"), corner_radius=10, command=self._save).pack(fill="x", padx=25, pady=20)

    def _on_ram_slider_change(self, value):
        snapped_val = round(value)
        self.ram_slider.set(snapped_val)
        self.ram_val_label.configure(text=f"Выделение ОЗУ: {int(snapped_val)} GB")

    def _browse_path(self):
        dir_selected = filedialog.askdirectory()
        if dir_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, dir_selected)

    def _save(self):
        ram_gb = int(round(self.ram_slider.get()))
        self.config["ram"] = f"{ram_gb}G"
        self.config["minecraft_dir"] = self.path_entry.get()
        self.config["jvm_args"] = self.jvm_entry.get()
        self.config["fullscreen"] = self.fullscreen_var.get()
        self.config["keep_open"] = self.keep_open_var.get()

        try:
            self.config["width"] = int(self.width_entry.get())
            self.config["height"] = int(self.height_entry.get())
        except ValueError:
            self.config["width"] = 854
            self.config["height"] = 480

        self.save_callback()
        self.destroy()


from concurrent.futures import ThreadPoolExecutor, as_completed


def find_system_java_21(mc_dir=None):
    candidates = []
    if "JAVA_HOME" in os.environ:
        candidates.append(os.path.join(os.environ["JAVA_HOME"], "bin", "javaw.exe"))
        candidates.append(os.path.join(os.environ["JAVA_HOME"], "bin", "java.exe"))

    if mc_dir:
        rt_dir = os.path.join(mc_dir, "runtime")
        if os.path.exists(rt_dir):
            for root, dirs, files in os.walk(rt_dir):
                for f in ["javaw.exe", "java.exe"]:
                    if f in files:
                        candidates.append(os.path.join(root, f))

    roots = [
        os.path.expanduser("~/.jdks"),
        r"C:\Program Files\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"C:\Program Files\BellSoft",
        r"C:\Program Files\Amazon Corretto",
        r"C:\Program Files (x86)\Java"
    ]
    for r in roots:
        if os.path.exists(r):
            for root, dirs, files in os.walk(r):
                for f in ["javaw.exe", "java.exe"]:
                    if f in files:
                        candidates.append(os.path.join(root, f))

    creation_flags = 0
    startupinfo = None
    if platform.system() == "Windows":
        creation_flags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    for c in candidates:
        if os.path.exists(c):
            try:
                out = subprocess.run(
                    [c, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=creation_flags,
                    startupinfo=startupinfo
                )
                err = out.stderr or out.stdout
                for ver_prefix in ["21.", "22.", "23.", "24.", "25."]:
                    if ver_prefix in err:
                        return c
            except Exception:
                pass
    return None


class TurboMinecraftInstaller:
    @staticmethod
    def install(version_name, fabric_loader_version, mc_dir, status_cb=None, prog_cb=None):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=3)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # 1. Загрузка и парсинг version.json
        version_dir = os.path.join(mc_dir, "versions", version_name)
        os.makedirs(version_dir, exist_ok=True)
        version_json_path = os.path.join(version_dir, f"{version_name}.json")
        version_jar_path = os.path.join(version_dir, f"{version_name}.jar")

        if not os.path.exists(version_json_path):
            if status_cb:
                status_cb(f"Получение манифеста {version_name}...")
            r = session.get("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=10)
            manifest = r.json()
            ver_entry = next((v for v in manifest["versions"] if v["id"] == version_name), None)
            if not ver_entry:
                raise Exception(f"Версия {version_name} не найдена в Mojang манифесте!")

            r_ver = session.get(ver_entry["url"], timeout=10)
            with open(version_json_path, "w", encoding="utf-8") as f:
                f.write(r_ver.text)

        with open(version_json_path, "r", encoding="utf-8") as f:
            v_data = json.load(f)

        # 2. Загрузка client.jar
        if not os.path.exists(version_jar_path) or os.path.getsize(version_jar_path) < 1000:
            if status_cb:
                status_cb(f"Загрузка {version_name}.jar...")
            client_dl = v_data.get("downloads", {}).get("client", {})
            if "url" in client_dl:
                r_jar = session.get(client_dl["url"], timeout=30)
                with open(version_jar_path, "wb") as f:
                    f.write(r_jar.content)

        # 3. Параллельная загрузка библиотек (32 потока)
        libraries = v_data.get("libraries", [])
        lib_tasks = []
        for lib in libraries:
            downloads = lib.get("downloads", {})
            artifact = downloads.get("artifact")
            if artifact and "url" in artifact and "path" in artifact:
                lib_path = os.path.join(mc_dir, "libraries", artifact["path"])
                if not os.path.exists(lib_path) or os.path.getsize(lib_path) == 0:
                    lib_tasks.append((artifact["url"], lib_path))

        if lib_tasks:
            if status_cb:
                status_cb(f"Быстрая загрузка библиотек (32 потока)...")
            done_cnt = 0
            total_cnt = len(lib_tasks)

            def dl_file(item):
                url, dst = item
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                resp = session.get(url, timeout=20)
                with open(dst, "wb") as f:
                    f.write(resp.content)

            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = [executor.submit(dl_file, t) for t in lib_tasks]
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        print("Ошибка загрузки библиотеки:", e)
                    done_cnt += 1
                    if prog_cb:
                        prog_cb(done_cnt / total_cnt)
                    if status_cb and done_cnt % 5 == 0:
                        status_cb(f"Библиотеки: {int((done_cnt / total_cnt) * 100)}%")

        # 4. Ресурсы игры (Assets) - параллельная загрузка (32 потока)
        asset_index_info = v_data.get("assetIndex")
        if asset_index_info and "url" in asset_index_info:
            asset_idx_id = asset_index_info.get("id", version_name)
            idx_dir = os.path.join(mc_dir, "assets", "indexes")
            idx_file = os.path.join(idx_dir, f"{asset_idx_id}.json")
            os.makedirs(idx_dir, exist_ok=True)

            if not os.path.exists(idx_file):
                r_idx = session.get(asset_index_info["url"], timeout=10)
                with open(idx_file, "w", encoding="utf-8") as f:
                    f.write(r_idx.text)

            with open(idx_file, "r", encoding="utf-8") as f:
                idx_data = json.load(f)

            objects = idx_data.get("objects", {})
            asset_tasks = []
            for obj_name, obj_info in objects.items():
                hash_val = obj_info.get("hash")
                if hash_val:
                    sub = hash_val[:2]
                    asset_dst = os.path.join(mc_dir, "assets", "objects", sub, hash_val)
                    if not os.path.exists(asset_dst) or os.path.getsize(asset_dst) == 0:
                        asset_url = f"https://resources.download.minecraft.net/{sub}/{hash_val}"
                        asset_tasks.append((asset_url, asset_dst))

            if asset_tasks:
                if status_cb:
                    status_cb(f"Быстрая загрузка ресурсов игры (32 потока)...")
                done_a = 0
                total_a = len(asset_tasks)

                def dl_asset(item):
                    url, dst = item
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    resp = session.get(url, timeout=15)
                    with open(dst, "wb") as f:
                        f.write(resp.content)

                with ThreadPoolExecutor(max_workers=32) as executor:
                    futures = [executor.submit(dl_asset, t) for t in asset_tasks]
                    for fut in as_completed(futures):
                        try:
                            fut.result()
                        except Exception as e:
                            print("Ошибка загрузки ресурса:", e)
                        done_a += 1
                        if prog_cb:
                            prog_cb(done_a / total_a)
                        if status_cb and done_a % 100 == 0:
                            status_cb(f"Ресурсы: {int((done_a / total_a) * 100)}%")

        # 5. Установка Fabric Loader
        fabric_profile_id = f"fabric-loader-{fabric_loader_version}-{version_name}"
        fabric_json_path = os.path.join(mc_dir, "versions", fabric_profile_id, f"{fabric_profile_id}.json")
        if not os.path.exists(fabric_json_path) or os.path.getsize(fabric_json_path) < 100:
            if status_cb:
                status_cb(f"Установка Fabric {fabric_loader_version}...")
            minecraft_launcher_lib.fabric.install_fabric(version_name, mc_dir, loader_version=fabric_loader_version)


# ========== ОСНОВНОЙ ЛАУНЧЕР ==========
class ThunderDLC:
    def __init__(self):
        self.load_config()
        self.game_process = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.window = ctk.CTk()
        self.window.title("ThunderDLC")
        
        # Центрирование главного окна на экране
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - WIDTH) // 2
        y = (screen_height - HEIGHT) // 2
        self.window.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
        self.window.resizable(False, False)

        ico_p = get_app_resource("icon.ico")
        if ico_p and os.path.exists(ico_p):
            try:
                self.window.wm_iconbitmap(os.path.abspath(ico_p))
                self.window.iconbitmap(os.path.abspath(ico_p))
            except Exception:
                pass

        icon_img = make_app_icon(64)
        self._icon_photo = ImageTk.PhotoImage(icon_img)
        self.window.iconphoto(True, self._icon_photo)

        # Win32 API для принудительной установки иконки в заголовок окна Windows
        def _apply_win32_icon():
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
                if not hwnd:
                    hwnd = self.window.winfo_id()
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                h_icon_small = ctypes.windll.user32.LoadImageW(None, ico_p, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                h_icon_big = ctypes.windll.user32.LoadImageW(None, ico_p, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                WM_SETICON = 0x0080
                if h_icon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_icon_small)
                if h_icon_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_icon_big)
            except Exception:
                pass

        if platform.system() == "Windows" and os.path.exists(ico_p):
            self.window.after(100, _apply_win32_icon)

        self.background = DynamicBackground(self.window, LEFT_W, HEIGHT)

        self.rpc = DiscordRPC(self.config.get("discord_client_id", "1544251893281202246"))
        threading.Thread(target=self.rpc.connect, daemon=True).start()

        self.build_ui()
        self.window.after(500, self.update_launcher_rpc)

        def _periodic_trim():
            trim_memory()
            self.window.after(30000, _periodic_trim)

        self.window.after(1500, _periodic_trim)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save_config()

        # Добавляем кастомные версии из .minecraft/versions/
        self._load_custom_versions()

    def _load_custom_versions(self):
        """Сканирует корневой .minecraft/versions/ и все подпапки в .minecraft/.versions/<subdir>/versions/ на кастомные профили."""
        base_mc_dir = os.path.abspath(self.config.get("minecraft_dir", "./.minecraft"))

        scan_dirs = []
        if os.path.isdir(base_mc_dir):
            scan_dirs.append(base_mc_dir)

        # Сканируем также .versions/ папку для поиска профилей
        versions_parent = os.path.join(base_mc_dir, ".versions")
        if os.path.isdir(versions_parent):
            for entry in os.listdir(versions_parent):
                subpath = os.path.join(versions_parent, entry)
                if os.path.isdir(subpath):
                    scan_dirs.append(subpath)

        existing_names = {v["name"] for v in self.config.get("versions", [])}
        existing_display = {v["display_name"] for v in self.config.get("versions", [])}

        custom_added = []
        for scan_root in scan_dirs:
            versions_dir = os.path.join(scan_root, "versions")
            if not os.path.isdir(versions_dir):
                continue
            for folder_name in sorted(os.listdir(versions_dir)):
                folder_path = os.path.join(versions_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                # Ищем .json файл профиля внутри папки
                json_path = os.path.join(folder_path, f"{folder_name}.json")
                if not os.path.exists(json_path):
                    continue

                # Парсим имя: fabric-loader-0.19.3-1.21.4 → mc_version=1.21.4, fabric=0.19.3
                if folder_name.startswith("fabric-loader-"):
                    parts = folder_name.split("-")
                    if len(parts) >= 4:
                        mc_ver = parts[-1]
                        loader_ver = parts[2]
                        display = f"[Custom] {mc_ver} Fabric"
                    else:
                        continue
                else:
                    mc_ver = folder_name
                    loader_ver = None
                    display = f"[Custom] {folder_name}"

                if mc_ver in existing_names or display in existing_display:
                    continue

                if scan_root == base_mc_dir:
                    mc_subdir = folder_name
                else:
                    mc_subdir = os.path.basename(scan_root)

                custom_entry = {
                    "name": mc_ver,
                    "display_name": display,
                    "type": "custom",
                    "fabric_version": loader_ver or "",
                    "mc_subdir": mc_subdir,
                    "profile_id": folder_name,
                    "mods": []
                }
                custom_added.append(custom_entry)
                existing_names.add(mc_ver)
                existing_display.add(display)

        if custom_added:
            self.config.setdefault("versions", []).extend(custom_added)

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def open_game_folder(self):
        base_mc_dir = os.path.abspath(self.config.get("minecraft_dir", "./.minecraft"))
        selected_display = self.version_menu.get()
        selected_version_data = next((v for v in self.config["versions"] if v["display_name"] == selected_display), None)
        
        if selected_version_data:
            mc_subdir = selected_version_data.get("mc_subdir", selected_version_data["name"])
            mc_dir = os.path.join(base_mc_dir, ".versions", mc_subdir)
        else:
            mc_dir = base_mc_dir

        os.makedirs(mc_dir, exist_ok=True)
        if platform.system() == "Windows":
            os.startfile(mc_dir)
        elif platform.system() == "Darwin":
            subprocess.run(["open", mc_dir])
        else:
            subprocess.run(["xdg-open", mc_dir])

    def open_vk_group(self):
        import webbrowser
        vk_url = self.config.get("vk_group", "https://vk.me/join/Vwe_cQ/FHhqZp_abcYo1GoDYOPzQ1GpMlsU=")
        webbrowser.open(vk_url)

    def build_ui(self):
        self.divider = ctk.CTkFrame(self.window, width=1, height=HEIGHT, fg_color=DIVIDER_COLOR)
        # ... дальше ваш код build_ui без изменений
        self.divider = ctk.CTkFrame(self.window, width=1, height=HEIGHT, fg_color=DIVIDER_COLOR)
        self.divider.place(x=LEFT_W, y=0)

        self.right_panel = ctk.CTkFrame(self.window, width=WIDTH - LEFT_W, height=HEIGHT, corner_radius=0, fg_color=RIGHT_PANEL_COLOR)
        self.right_panel.place(x=LEFT_W, y=0)

        self.title_label = ctk.CTkLabel(self.window, text="ThunderDLC", font=ctk.CTkFont(size=30, weight="bold"), text_color="#FFFFFF", fg_color=RIGHT_PANEL_COLOR)
        self.title_label.place(x=RIGHT_X, y=55, anchor="w")

        self.status_label = ctk.CTkLabel(self.window, text="Готов к запуску", font=ctk.CTkFont(size=13), text_color="#888888", fg_color=RIGHT_PANEL_COLOR)
        self.status_label.place(x=RIGHT_X, y=95, anchor="w")

        self.nick_label = ctk.CTkLabel(self.window, text="НИКНЕЙМ", font=ctk.CTkFont(size=11), text_color="#777777", fg_color=RIGHT_PANEL_COLOR)
        self.nick_label.place(x=RIGHT_X, y=145, anchor="w")

        self.nick_entry = ctk.CTkEntry(
            self.window,
            placeholder_text="👤 Введите ник",
            width=FIELD_W,
            height=44,
            font=ctk.CTkFont(size=14),
            fg_color=INPUT_COLOR,
            border_color=INPUT_BORDER,
            border_width=1,
            corner_radius=10,
            text_color="#FFFFFF"
        )
        self.nick_entry.place(x=RIGHT_X, y=175, anchor="w")
        self.nick_entry.insert(0, self.config.get("default_nick", ""))

        self.version_label = ctk.CTkLabel(self.window, text="ВЕРСИЯ И СБОРКА", font=ctk.CTkFont(size=11), text_color="#777777", fg_color=RIGHT_PANEL_COLOR)
        self.version_label.place(x=RIGHT_X, y=235, anchor="w")

        version_names = [v["display_name"] for v in self.config["versions"]]
        saved_ver = self.config.get("selected_version", "")
        initial_ver = version_names[0] if version_names else ""
        for v in self.config["versions"]:
            if v.get("name") == saved_ver or v.get("display_name") == saved_ver:
                initial_ver = v["display_name"]
                break

        def _on_version_select(choice):
            self.config["selected_version"] = choice
            self.save_config()
            self.update_launcher_rpc()

        self.version_menu = ctk.CTkOptionMenu(
            self.window,
            values=version_names,
            width=FIELD_W,
            height=44,
            fg_color=INPUT_COLOR,
            button_color="#222222",
            button_hover_color="#333333",
            corner_radius=10,
            command=_on_version_select
        )
        if initial_ver:
            self.version_menu.set(initial_ver)
        self.version_menu.place(x=RIGHT_X, y=265, anchor="w")

        self.play_button = ctk.CTkButton(
            self.window,
            text="Запустить игру →",
            width=FIELD_W,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=BTN_COLOR,
            hover_color=BTN_HOVER,
            corner_radius=10,
            border_color="#444444",
            border_width=1,
            command=self.start_launch
        )
        self.play_button.place(x=RIGHT_X, y=385, anchor="w")

        self.progress = ctk.CTkProgressBar(self.window, width=FIELD_W, height=5, fg_color=INPUT_COLOR, progress_color="#888888")
        self.progress.place(x=RIGHT_X, y=428, anchor="w")
        self.progress.set(0)

        # Нижняя панель кнопок (ВКонтакте, Папка, Настройки)
        btn_w = 144
        self.vk_btn = ctk.CTkButton(
            self.window,
            text="💬 ВКонтакте",
            width=btn_w,
            height=36,
            fg_color=INPUT_COLOR,
            hover_color=BTN_HOVER,
            border_color=INPUT_BORDER,
            border_width=1,
            corner_radius=8,
            command=self.open_vk_group
        )
        self.vk_btn.place(x=RIGHT_X, y=485, anchor="w")

        self.folder_btn = ctk.CTkButton(
            self.window,
            text="📁 Папка игры",
            width=btn_w,
            height=36,
            fg_color=INPUT_COLOR,
            hover_color=BTN_HOVER,
            border_color=INPUT_BORDER,
            border_width=1,
            corner_radius=8,
            command=self.open_game_folder
        )
        self.folder_btn.place(x=RIGHT_X + 156, y=485, anchor="w")

        self.settings_btn = ctk.CTkButton(
            self.window,
            text="⚙  Настройки",
            width=btn_w,
            height=36,
            fg_color=INPUT_COLOR,
            hover_color=BTN_HOVER,
            border_color=INPUT_BORDER,
            border_width=1,
            corner_radius=8,
            command=self.open_settings
        )
        self.settings_btn.place(x=RIGHT_X + 312, y=485, anchor="w")

    def update_launcher_rpc(self):
        try:
            nick = self.nick_entry.get().strip() if hasattr(self, "nick_entry") else self.config.get("default_nick", "")
            selected_ver = self.version_menu.get() if hasattr(self, "version_menu") else self.config.get("selected_version", "1.21.11")

            self.rpc.update_presence(
                details=f"Nickname: {nick}" if nick else "In Launcher Menu",
                state=f"Selected: {selected_ver}",
                large_image="app_icon",
                large_text=f"ThunderDLC Client ({selected_ver})",
                small_image="fabric",
                small_text="Fabric Client"
            )
        except Exception:
            pass

    def _monitor_game_log(self, mc_dir, nick, version_name, game_start_time):
        log_file = os.path.join(mc_dir, "logs", "latest.log")

        self.rpc.update_presence(
            details=f"Nickname: {nick}",
            state="In Main Menu",
            large_image="app_icon",
            large_text=f"ThunderDLC {version_name}",
            start_time=game_start_time
        )

        last_pos = 0
        detected_log_cheats = []
        if os.path.exists(log_file):
            try:
                last_pos = os.path.getsize(log_file)
            except Exception:
                pass

        while self.game_process and self.game_process.poll() is None:
            time.sleep(1.5)
            if not os.path.exists(log_file):
                continue
            try:
                curr_size = os.path.getsize(log_file)
                if curr_size > last_pos:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                    # Сканирование логов Fabric Loader на запуск сторонних чит-модов (без ложных срабатываний на ресурспаки и чат)
                    for line in new_lines:
                        l_lower = line.lower()
                        # Пропускаем строки ресурспаков, текстур, звуков и чата
                        if any(skip_w in l_lower for skip_w in ["resourcemanager", "resourcepack", "textures/", "sounds/", "[chat]", "unifont", "atlas"]):
                            pass
                        elif ("loading " in l_lower and "mod" in l_lower) or l_lower.strip().startswith("- "):
                            for c_pat in ["dd 1.0.0", "doomsday", "cortex", "mhub", "releon", "meteor", "thunderhack", "celestial", "expensive", "nursultan", "wurst"]:
                                if c_pat in l_lower and f"[{c_pat.title()}]" not in detected_log_cheats:
                                    detected_log_cheats.append(f"[{c_pat.title()}]")

                        if "Connecting to " in line:
                            ignore_words = ["voice", "websocket", "socket", "auth", "session", "endpoint", "realms", "http", "https", "worker", "server"]
                            match = re.search(r"Connecting to\s+([a-zA-Z0-9.\-_]+)(?:,\s*(\d+))?", line)
                            if match:
                                server_host = match.group(1).rstrip(",").strip()
                                port = match.group(2)
                                if server_host.lower() not in ignore_words and ("." in server_host or server_host.lower() == "localhost" or port):
                                    # Проверка FunTime Guard на запрещенные правилами FunTime моды и читы
                                    if "funtime" in server_host.lower():
                                        forbidden = scan_forbidden_mods(mc_dir)
                                        for dc in detected_log_cheats:
                                            if dc not in forbidden:
                                                forbidden.append(dc)
                                        if forbidden:
                                            self.rpc.update_presence(
                                                details=f"Nickname: {nick}",
                                                state="⚠️ FunTime (Blocked: Bad Mods)",
                                                large_text=f"ThunderDLC {version_name}",
                                                start_time=game_start_time
                                            )
                                            self.window.after(0, lambda h=server_host, m=forbidden: self._open_fake_ban(h, nick, m, mc_dir))
                                            continue

                                    self.rpc.update_presence(
                                        details=f"Nickname: {nick}",
                                        state=f"Server: {server_host}",
                                        large_text=f"ThunderDLC {version_name}",
                                        start_time=game_start_time
                                    )
                        elif "Starting integrated minecraft server" in line:
                            self.rpc.update_presence(
                                details=f"Playing as: {nick}",
                                state="Singleplayer World",
                                large_image="app_icon",
                                large_text=f"ThunderDLC {version_name}",
                                start_time=game_start_time
                            )
                        elif "Stopping worker threads" in line or "Disconnecting from" in line:
                            self.rpc.update_presence(
                                details=f"Playing as: {nick}",
                                state="In Main Menu",
                                large_image="app_icon",
                                large_text=f"ThunderDLC {version_name}",
                                start_time=game_start_time
                            )
            except Exception:
                pass

    def open_settings(self):
        SettingsWindow(self.window, self.config, self.save_config)

    def _open_fake_ban(self, server_host, nick, forbidden, mc_dir):
        try:
            self.window.deiconify()
        except Exception:
            pass
        FakeBanWindow(server_host, nick, forbidden, mc_dir)

    def set_status(self, text, color="#888888"):
        self.status_label.configure(text=text, text_color=color)

    def set_progress_val(self, val):
        self.progress.set(val)

    def start_launch(self):
        if self.game_process and self.game_process.poll() is None:
            try:
                self.game_process.terminate()
            except Exception:
                pass
            return

        nick = self.nick_entry.get().strip()
        if not nick:
            self.set_status("Введите ник!", "#FF5555")
            return

        selected_display = self.version_menu.get()
        self.config["default_nick"] = nick
        self.config["selected_version"] = selected_display
        self.save_config()

        selected_version_data = next((v for v in self.config["versions"] if v["display_name"] == selected_display), self.config["versions"][0])

        self.play_button.configure(state="disabled")
        threading.Thread(target=self.launch_game, args=(nick, selected_version_data)).start()

    def launch_game(self, nick, version_data):
        try:
            base_mc_dir = os.path.abspath(self.config.get("minecraft_dir", "./.minecraft"))
            # Каждая версия в своей подпапке внутри .versions/ (.minecraft/.versions/1.21.11/, .minecraft/.versions/1.21.4/ и т.д.)
            mc_subdir = version_data.get("mc_subdir", version_data["name"])
            mc_dir = os.path.join(base_mc_dir, ".versions", mc_subdir)
            os.makedirs(mc_dir, exist_ok=True)

            apply_default_mc_options(mc_dir)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            for bg_name in ["bg_menu.gif", "bg.jpg", "icon.png"]:
                src_bg = os.path.join(base_dir, bg_name)
                dst_bg = os.path.join(mc_dir, bg_name)
                if os.path.exists(src_bg) and not os.path.exists(dst_bg):
                    shutil.copy2(src_bg, dst_bg)

            version_name = version_data["name"]
            # Берём fabric_version из version_data, если не задан — из глобального конфига
            fabric_loader_version = version_data.get("fabric_version") or self.config.get("fabric_version", "0.19.3")
            version_type = version_data.get("type", "fabric")

            # 1. Скачивание только недостающих модов ВЫБРАННОЙ версии
            mods_list = version_data.get("mods", [])
            missing_mods = []
            for mod in mods_list:
                rel_path = mod.get("path")
                if rel_path:
                    fp = os.path.join(mc_dir, rel_path)
                else:
                    fn = mod.get("name", mod.get("url", "").split("/")[-1].split("?")[0])
                    fp = os.path.join(mc_dir, "mods", fn)
                if not os.path.exists(fp) or os.path.getsize(fp) == 0:
                    missing_mods.append(mod)

            if missing_mods:
                self.set_status("Скачивание модов...", "#AAAAAA")
                ModsManager.download_all(missing_mods, mc_dir, lambda v, t: (self.set_progress_val(v), self.set_status(t, "#AAAAAA")))
                self.set_progress_val(0)

            # 2. Установка версии и Fabric — только для НЕ кастомных версий (используем общий base_mc_dir)
            if version_type != "custom":
                def status_callback(text):
                    self.set_status(text, "#AAAAAA")

                def progress_callback(pct):
                    self.set_progress_val(pct)

                TurboMinecraftInstaller.install(version_name, fabric_loader_version, base_mc_dir, status_callback, progress_callback)
                self.set_progress_val(0)

            # 3. Мгновенный поиск Java 21 на ПК
            self.set_status("Подготовка Java 21...", "#AAAAAA")
            java_exec = find_system_java_21(base_mc_dir)

            if not java_exec or not os.path.exists(java_exec):
                # Резервная загрузка только если Java 21 вообще нет на компьютере (сохраняем в общую папку)
                custom_java_dir = os.path.join(base_mc_dir, "runtime", "java-21-adoptium")
                custom_java_bin = os.path.join(custom_java_dir, "bin", "javaw.exe" if platform.system() == "Windows" else "java")
                if os.path.exists(custom_java_bin):
                    java_exec = custom_java_bin
                else:
                    self.set_status("Загрузка Java 21 (Adoptium)...", "#AAAAAA")
                    os.makedirs(os.path.join(base_mc_dir, "runtime"), exist_ok=True)
                    jdk_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jdk_x64_windows_hotspot_21.0.3_9.zip"
                    zip_path = os.path.join(base_mc_dir, "runtime", "java21.zip")
                    temp_extract_dir = os.path.join(base_mc_dir, "runtime", "temp_java")
                    req = urllib.request.Request(jdk_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as resp, open(zip_path, 'wb') as out_file:
                        out_file.write(resp.read())
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_extract_dir)
                    subfolder = os.listdir(temp_extract_dir)[0]
                    shutil.move(os.path.join(temp_extract_dir, subfolder), custom_java_dir)
                    shutil.rmtree(temp_extract_dir)
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    java_exec = custom_java_bin

            if not java_exec or not os.path.exists(java_exec):
                self.set_status("Ошибка: Не найдена Java 21!", "#FF5555")
                self.play_button.configure(state="normal")
                return

            # Определяем profile_id: для custom — берём из version_data['profile_id'],
            # для fabric — стандартный fabric-loader-X.Y.Z-mc_ver
            if version_type == "custom":
                fabric_profile_id = version_data.get("profile_id", f"fabric-loader-{fabric_loader_version}-{version_name}")
            else:
                fabric_profile_id = f"fabric-loader-{fabric_loader_version}-{version_name}"

            self.set_status("Запуск игры...", "#CCCCCC")

            target_window_title = f"ThunderDLC {version_name}"

            jvm_args_list = [
                f"-Xmx{self.config['ram']}",
                f"-Xms{self.config['ram']}",
                # Встроенная ультра-оптимизация под Minecraft
                "-XX:+UnlockExperimentalVMOptions",
                "-XX:+UseG1GC",
                "-XX:G1NewSizePercent=20",
                "-XX:G1ReservePercent=15",
                "-XX:MaxGCPauseMillis=25",
                "-XX:G1HeapRegionSize=32M",
                "-XX:G1MixedGCCountTarget=4",
                "-XX:InitiatingHeapOccupancyPercent=15",
                "-XX:G1MixedGCLiveThresholdPercent=90",
                "-XX:G1RSetUpdatingPauseTimePercent=5",
                "-XX:SurvivorRatio=32",
                "-XX:+PerfDisableSharedMem",
                "-XX:MaxTenuringThreshold=1",
                "-XX:+ParallelRefProcEnabled",
                "-XX:+AlwaysPreTouch",  # Выделяет память заранее, убирая лаги и зависания 'Не отвечает'
                # Быстрый байткод и JIT компилятор
                "-XX:+TieredCompilation",
                "-XX:+UseStringDeduplication",
                "-XX:+OptimizeStringConcat",
                "-Dfml.ignorePatchDiscrepancies=true",
                "-Dfml.ignoreInvalidMinecraftCertificates=true",
                # Аппаратное ускорение OpenGL и отключение софтверного DirectDraw
                "-Dsun.java2d.opengl=true",
                "-Dsun.java2d.noddraw=true",
                "-Dsun.java2d.pmoffscreen=true",
                # Защита от инжекта читов (блокируем JVM Attach API)
                "-XX:+DisableAttachMechanism",
                "-Djdk.attach.allowAttachSelf=false",
                f"-Dwindow.title={target_window_title}",
                f"-Dminecraft.app.title={target_window_title}"
            ]
            custom_args = self.config.get("jvm_args", "").strip()
            if custom_args:
                jvm_args_list.extend(custom_args.split())

            player_uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{nick}"))

            options = {
                "username": nick,
                "uuid": player_uuid,
                "token": "0",
                "executablePath": java_exec,
                "jvmArguments": jvm_args_list,
                "gameDirectory": mc_dir,  # Изолированный профиль
                "customResolution": not self.config.get("fullscreen", False),
                "resolutionWidth": str(self.config.get("width", 854)),
                "resolutionHeight": str(self.config.get("height", 480))
            }

            command = minecraft_launcher_lib.command.get_minecraft_command(fabric_profile_id, base_mc_dir, options)
            command.extend(["--windowTitle", target_window_title])

            if self.config.get("fullscreen", False):
                command.append("--fullscreen")

            # 6. Окружение GPU
            env = os.environ.copy()
            env["__NV_PRIME_RENDER_OFFLOAD"] = "1"
            env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
            env["SHIM_MCCOMPAT"] = "0x800000001"

            # 7. Запуск игры и автоматическое скрытие/возврат окна лаунчера
            self.window.after(600, self.window.withdraw)
            self.window.after(1000, trim_memory)

            popen_kwargs = {"cwd": mc_dir, "env": env}
            if platform.system() == "Windows":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                popen_kwargs["startupinfo"] = si

            self.game_process = subprocess.Popen(command, **popen_kwargs)
            game_start_time = int(time.time())
            threading.Thread(target=self._monitor_game_log, args=(mc_dir, nick, version_name, game_start_time), daemon=True).start()
            self.game_process.wait()

            # 8. При выходе из Майнкрафта снова открываем клиент
            self.game_process = None

            def _restore_client():
                try:
                    self.window.deiconify()
                    self.window.lift()
                    self.window.focus_force()
                    self.set_status("Готов к запуску", "#888888")
                    self.play_button.configure(
                        text="Запустить игру →",
                        fg_color=BTN_COLOR,
                        hover_color=BTN_HOVER,
                        state="normal"
                    )
                    self.update_launcher_rpc()
                except Exception:
                    pass

            self.window.after(100, _restore_client)

        except Exception as e:
            def _show_err():
                self.window.deiconify()
                self.set_status(f"Ошибка: {str(e)[:40]}", "#FF5555")
                self.play_button.configure(
                    text="Запустить игру →",
                    fg_color=BTN_COLOR,
                    hover_color=BTN_HOVER,
                    state="normal"
                )
            self.window.after(0, _show_err)
            print(f"Ошибка запуска: {e}")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = ThunderDLC()
    app.run()