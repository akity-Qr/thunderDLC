import os
import sys
import shutil
import threading
import subprocess
import winreg
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# Цветовая палитра ThunderDLC (Dark Glass / Neon Blue)
BG_COLOR = "#0D0E15"
CARD_BG = "#161722"
ACCENT_BLUE = "#3B82F6"
ACCENT_HOVER = "#2563EB"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#9CA3AF"
BORDER_COLOR = "#2A2D3D"

class ThunderDLCInstaller(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ThunderDLC Setup")
        self.geometry("580x490")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)

        # Центрирование окна на экране
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.base_dir = self.find_source_dir()

        # Установка иконки окна
        ico_path = os.path.abspath(os.path.join(self.base_dir, "icon.ico"))
        if os.path.exists(ico_path):
            try:
                self.wm_iconbitmap(ico_path)
                self.iconbitmap(ico_path)
            except Exception:
                pass

        def _apply_win32_icon():
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if not hwnd:
                    hwnd = self.winfo_id()
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                h_icon_small = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                h_icon_big = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                WM_SETICON = 0x0080
                if h_icon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_icon_small)
                if h_icon_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_icon_big)
            except Exception:
                pass

        if os.path.exists(ico_path):
            self.after(100, _apply_win32_icon)

        self.default_install_dir = r"C:\ThunderDLC"
        self.install_dir_var = tk.StringVar(value=self.default_install_dir)
        self.create_desktop_shortcut_var = tk.BooleanVar(value=True)
        self.create_start_shortcut_var = tk.BooleanVar(value=True)
        self.launch_after_var = tk.BooleanVar(value=True)

        self.is_installing = False

        self.build_ui()

    def find_source_dir(self):
        candidates = [
            getattr(sys, '_MEIPASS', ''),
            os.path.dirname(os.path.abspath(__file__)),
            r"C:\Users\akity\OneDrive\Desktop\ThunderDLC",
            os.path.join(r"C:\Users\akity\OneDrive\Desktop\ThunderDLC", "dist")
        ]
        for c in candidates:
            if c and (os.path.exists(os.path.join(c, "ThunderDLC.exe")) or os.path.exists(os.path.join(c, "launcher.py"))):
                return c
        return os.path.dirname(os.path.abspath(__file__))

    def get_desktop_directories(self):
        desktops = []
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            val, _ = winreg.QueryValueEx(key, "Desktop")
            desktops.append(os.path.expandvars(val))
        except Exception:
            pass

        onedrive = os.environ.get("OneDrive")
        if onedrive:
            desktops.append(os.path.join(onedrive, "Desktop"))

        desktops.append(r"C:\Users\akity\OneDrive\Desktop")
        desktops.append(os.path.join(os.path.expanduser("~"), "Desktop"))

        # Возвращаем уникальные существующие пути
        result = []
        for d in desktops:
            if d and os.path.exists(d) and d not in result:
                result.append(d)
        return result

    def build_ui(self):
        # 1. Шапка (Логотип + Заголовок)
        header_frame = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header_frame.pack(fill="x", padx=16, pady=(14, 10))

        # Иконка
        png_path = os.path.join(self.base_dir, "icon.png")
        if os.path.exists(png_path):
            try:
                img = Image.open(png_path).resize((44, 44), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(header_frame, image=self.logo_img, bg=CARD_BG)
                logo_lbl.pack(side="left", padx=14, pady=10)
            except Exception:
                pass

        title_box = tk.Frame(header_frame, bg=CARD_BG)
        title_box.pack(side="left", fill="both", expand=True, pady=10)

        title_lbl = tk.Label(title_box, text="ThunderDLC", font=("Segoe UI", 16, "bold"), fg=TEXT_WHITE, bg=CARD_BG)
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(title_box, text="Мастер установки клиента и лаунчера на ваш компьютер", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # 2. Карточка выбора папки установки
        folder_card = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        folder_card.pack(fill="x", padx=16, pady=4)

        path_title = tk.Label(folder_card, text="Папка установки (Локальный диск C):", font=("Segoe UI", 10, "bold"), fg=TEXT_WHITE, bg=CARD_BG)
        path_title.pack(anchor="w", padx=14, pady=(10, 6))

        path_input_box = tk.Frame(folder_card, bg=CARD_BG)
        path_input_box.pack(fill="x", padx=14, pady=(0, 12))

        self.path_entry = tk.Entry(
            path_input_box,
            textvariable=self.install_dir_var,
            font=("Segoe UI", 10),
            bg="#0F1017",
            fg=TEXT_WHITE,
            insertbackground=TEXT_WHITE,
            relief="flat",
            highlightbackground="#2A2D3D",
            highlightcolor=ACCENT_BLUE,
            highlightthickness=1
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        browse_btn = tk.Button(
            path_input_box,
            text="Обзор...",
            font=("Segoe UI", 9, "bold"),
            bg="#222533",
            fg=TEXT_WHITE,
            activebackground="#2D3142",
            activeforeground=TEXT_WHITE,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.browse_folder
        )
        browse_btn.pack(side="right")

        # 3. Опции установки
        options_card = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        options_card.pack(fill="x", padx=16, pady=4)

        opts_title = tk.Label(options_card, text="Дополнительные параметры:", font=("Segoe UI", 10, "bold"), fg=TEXT_WHITE, bg=CARD_BG)
        opts_title.pack(anchor="w", padx=14, pady=(8, 4))

        c1 = tk.Checkbutton(
            options_card,
            text="Создать ярлык ThunderDLC на Рабочем столе",
            variable=self.create_desktop_shortcut_var,
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_WHITE,
            activebackground=CARD_BG,
            activeforeground=TEXT_WHITE,
            selectcolor="#0F1017",
            cursor="hand2"
        )
        c1.pack(anchor="w", padx=14, pady=2)

        c2 = tk.Checkbutton(
            options_card,
            text="Добавить ярлык в меню «Пуск»",
            variable=self.create_start_shortcut_var,
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_WHITE,
            activebackground=CARD_BG,
            activeforeground=TEXT_WHITE,
            selectcolor="#0F1017",
            cursor="hand2"
        )
        c2.pack(anchor="w", padx=14, pady=2)

        c3 = tk.Checkbutton(
            options_card,
            text="Запустить ThunderDLC после завершения установки",
            variable=self.launch_after_var,
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_WHITE,
            activebackground=CARD_BG,
            activeforeground=TEXT_WHITE,
            selectcolor="#0F1017",
            cursor="hand2"
        )
        c3.pack(anchor="w", padx=14, pady=(2, 8))

        # 4. Прогресс-бар и статус
        self.status_lbl = tk.Label(self, text="Готов к установке", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_COLOR)
        self.status_lbl.pack(anchor="w", padx=18, pady=(6, 2))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Thunder.Horizontal.TProgressbar",
            troughcolor="#1A1C28",
            background=ACCENT_BLUE,
            darkcolor=ACCENT_BLUE,
            lightcolor=ACCENT_BLUE,
            bordercolor="#1A1C28",
            thickness=6
        )

        self.prog_bar = ttk.Progressbar(self, style="Thunder.Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.prog_bar.pack(fill="x", padx=18, pady=(0, 10))

        # 5. Нижняя панель с кнопками
        bottom_frame = tk.Frame(self, bg=BG_COLOR)
        bottom_frame.pack(fill="x", padx=18, pady=(4, 16))

        self.install_btn = tk.Button(
            bottom_frame,
            text="⚡ УСТАНОВИТЬ",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT_BLUE,
            fg=TEXT_WHITE,
            activebackground=ACCENT_HOVER,
            activeforeground=TEXT_WHITE,
            relief="flat",
            cursor="hand2",
            padx=24,
            pady=8,
            command=self.start_installation
        )
        self.install_btn.pack(side="right", padx=(8, 0))

        self.cancel_btn = tk.Button(
            bottom_frame,
            text="Отмена",
            font=("Segoe UI", 10),
            bg="#222533",
            fg=TEXT_MUTED,
            activebackground="#2D3142",
            activeforeground=TEXT_WHITE,
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=8,
            command=self.destroy
        )
        self.cancel_btn.pack(side="right")

    def browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get(), title="Выберите папку для установки ThunderDLC")
        if chosen:
            chosen = os.path.normpath(chosen)
            if not chosen.endswith("ThunderDLC"):
                chosen = os.path.join(chosen, "ThunderDLC")
            self.install_dir_var.set(chosen)

    def set_status(self, text, pct=None):
        self.status_lbl.configure(text=text)
        if pct is not None:
            self.prog_bar["value"] = pct
        self.update_idletasks()

    def start_installation(self):
        if self.is_installing:
            return

        target_dir = self.install_dir_var.get().strip()
        if not target_dir:
            messagebox.showerror("Ошибка", "Укажите корректную папку установки!")
            return

        self.is_installing = True
        self.install_btn.configure(state="disabled", bg="#333748")
        self.cancel_btn.configure(state="disabled")
        self.path_entry.configure(state="disabled")

        threading.Thread(target=self.run_install_thread, args=(target_dir,), daemon=True).start()

    def run_install_thread(self, target_dir):
        try:
            self.set_status("Создание директории клиента...", 15)
            os.makedirs(target_dir, exist_ok=True)

            # 1. Извлекаем и копируем единый исполняемый лаунчер ThunderDLC.exe (все ресурсы внутри)
            self.set_status("Установка ThunderDLC.exe...", 50)

            exe_src = None
            if hasattr(sys, '_MEIPASS'):
                p = os.path.join(sys._MEIPASS, "ThunderDLC.exe")
                if os.path.exists(p):
                    exe_src = p

            if not exe_src:
                search_dirs = [
                    self.base_dir,
                    os.path.dirname(os.path.abspath(__file__)),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist"),
                    r"C:\Users\akity\OneDrive\Desktop\ThunderDLC\dist",
                    r"C:\Users\akity\OneDrive\Desktop\ThunderDLC"
                ]
                for d in search_dirs:
                    if d and os.path.exists(os.path.join(d, "ThunderDLC.exe")):
                        exe_src = os.path.join(d, "ThunderDLC.exe")
                        break

            if not exe_src or not os.path.exists(exe_src):
                raise RuntimeError("Критическая ошибка: ThunderDLC.exe не найден в дистрибутиве установщика!")

            installed_exe = os.path.join(target_dir, "ThunderDLC.exe")
            shutil.copy2(exe_src, installed_exe)

            # Копируем иконку в целевую папку для надежного ярлыка
            ico_src = None
            if hasattr(sys, '_MEIPASS'):
                p_ico = os.path.join(sys._MEIPASS, "icon.ico")
                if os.path.exists(p_ico):
                    ico_src = p_ico
            if not ico_src:
                for d in [self.base_dir, os.path.dirname(os.path.abspath(__file__))]:
                    if d and os.path.exists(os.path.join(d, "icon.ico")):
                        ico_src = os.path.join(d, "icon.ico")
                        break

            target_ico = os.path.join(target_dir, "icon.ico")
            if ico_src and os.path.exists(ico_src):
                try:
                    shutil.copy2(ico_src, target_ico)
                except Exception:
                    pass

            shortcut_icon = target_ico if os.path.exists(target_ico) else installed_exe

            # 2. Создание ярлыков на Рабочем столе (с учетом OneDrive Desktop)
            self.set_status("Создание ярлыков на Рабочем столе...", 85)

            if self.create_desktop_shortcut_var.get():
                desktop_dirs = self.get_desktop_directories()
                for d in desktop_dirs:
                    shortcut_path = os.path.join(d, "ThunderDLC.lnk")
                    self.create_windows_shortcut(shortcut_path, installed_exe, "", target_dir, shortcut_icon)

            if self.create_start_shortcut_var.get():
                appdata_start = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
                if os.path.exists(appdata_start):
                    shortcut_path = os.path.join(appdata_start, "ThunderDLC.lnk")
                    self.create_windows_shortcut(shortcut_path, installed_exe, "", target_dir, shortcut_icon)

            self.set_status("Установка успешно завершена!", 100)

            if self.launch_after_var.get():
                try:
                    if os.path.exists(installed_exe):
                        if platform.system() == "Windows":
                            os.startfile(installed_exe)
                        else:
                            clean_env = os.environ.copy()
                            for var in ['_MEIPASS2', '_MEIPASS', 'PYTHONHOME', 'PYTHONPATH']:
                                clean_env.pop(var, None)
                            subprocess.Popen([installed_exe], cwd=target_dir, env=clean_env)
                    else:
                        clean_env = os.environ.copy()
                        for var in ['_MEIPASS2', '_MEIPASS', 'PYTHONHOME', 'PYTHONPATH']:
                            clean_env.pop(var, None)
                        subprocess.Popen([sys.executable, os.path.join(target_dir, "launcher.py")], cwd=target_dir, env=clean_env)
                except Exception as ex:
                    print(f"Ошибка автозапуска: {ex}")

            self.after(500, self.finish_success)

        except Exception as e:
            self.set_status(f"Ошибка установки: {e}", 0)
            messagebox.showerror("Ошибка установки", f"Произошла ошибка при установке:\n{e}")
            self.install_btn.configure(state="normal", bg=ACCENT_BLUE)
            self.cancel_btn.configure(state="normal")
            self.path_entry.configure(state="normal")
            self.is_installing = False

    def create_windows_shortcut(self, shortcut_path, target_exe, args, working_dir, icon_path):
        ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.Arguments = '{args}'
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.IconLocation = "{icon_path}"
$Shortcut.Description = "ThunderDLC Client"
$Shortcut.Save()
'''
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=si
        )

    def finish_success(self):
        messagebox.showinfo("Установка завершена", f"ThunderDLC Client успешно установлен в:\n{self.install_dir_var.get()}\n\nЯрлык создан на Рабочем столе.")
        self.destroy()

if __name__ == "__main__":
    app = ThunderDLCInstaller()
    app.mainloop()
