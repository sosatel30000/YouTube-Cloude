# gui.py - YouCloud YTV2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import tempfile
import shutil
import threading
import webbrowser
from datetime import datetime

from encoder import YouTubeEncoder
from decoder import YouTubeDecoder
from archive import ArchiveManager
from downloader import YouTubeDownloader
from youtube_uploader import YouTubeUploader


class YouTubeStorageGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouCloud - YouTube File Storage YTV2")
        self.root.geometry("620x600")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')
        
        self.key = self.read_key_from_file()
        self.compress_after_encode = tk.BooleanVar(value=True)
        self.compression_level = tk.IntVar(value=9)
        self.downloader = None
        
        self.setup_ui()
    
    def read_key_from_file(self, key_file='key.txt'):
        try:
            if os.path.exists(key_file):
                with open(key_file, 'r', encoding='utf-8') as f:
                    key = f.read().strip()
                    return key if key else None
        except:
            pass
        return None
    
    def save_key_to_file(self, key):
        with open('key.txt', 'w', encoding='utf-8') as f:
            f.write(key)
        self.key = key
    
    def open_guide(self):
        guide_file = "guide.txt"
        if os.path.exists(guide_file):
            webbrowser.open(guide_file)
        else:
            with open(guide_file, 'w', encoding='utf-8') as f:
                f.write("""========================================
РУКОВОДСТВО ПО ЗАГРУЗКЕ НА YOUTUBE
========================================

1. ПОЛУЧЕНИЕ client_secret.json:
   - Перейдите на https://console.cloud.google.com/
   - Создайте новый проект
   - Включите YouTube Data API v3
   - Настройте экран согласия OAuth (External)
   - Создайте OAuth 2.0 Client ID (Desktop app)
   - Скачайте JSON и переименуйте в client_secret.json
   - Поместите файл в папку с программой

2. ПЕРВАЯ ЗАГРУЗКА:
   - При первой загрузке откроется браузер
   - Войдите в свой Google аккаунт
   - Разрешите доступ приложению
   - Токен сохранится для следующих раз

3. ПРИВАТНОСТЬ ВИДЕО:
   - public: видео увидят все
   - unlisted: видео только по ссылке
   - private: видео видите только вы

4. ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ YTV2:
   - Разрешение: 1920x1080
   - FPS: 15
   - Блоки: 8x8 пикселей
   - 16 цветов (4 бита на блок)
""")
            webbrowser.open(guide_file)
    
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(title_frame, text="☁️ YouCloud - YouTube File Storage", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        if os.path.exists("youcloud.ico"):
            self.root.iconbitmap("youcloud.ico")
        
        
       
           
        self.encrypt_indicator = tk.Canvas(title_frame, width=12, height=12, bg='#f0f0f0', highlightthickness=0)
        self.encrypt_indicator.pack(side=tk.RIGHT, padx=5)
        self.update_encrypt_indicator()
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        encode_tab = ttk.Frame(notebook, padding="8")
        notebook.add(encode_tab, text="📤 Кодировать")
        self.setup_encode_tab(encode_tab)
        
        decode_tab = ttk.Frame(notebook, padding="8")
        notebook.add(decode_tab, text="📥 Декодировать")
        self.setup_decode_tab(decode_tab)
        
        download_tab = ttk.Frame(notebook, padding="8")
        notebook.add(download_tab, text="⬇️ Скачать видео")
        self.setup_download_tab(download_tab)
        
        settings_tab = ttk.Frame(notebook, padding="8")
        notebook.add(settings_tab, text="⚙️ Настройки")
        self.setup_settings_tab(settings_tab)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(main_frame, text="✅ Готов", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(0, 5))
        
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding="3")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70, 
                                                   font=('Consolas', 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log("=" * 50)
        self.log("☁️ YouCloud запущена")
        self.log(f"🔐 Шифрование: {'Включено' if self.key else 'Выключено'}")
        self.log("📐 YTV2: 1920x1080, 15 FPS, блоки 8x8")
        self.log("=" * 50)
    
    def update_encrypt_indicator(self):
        self.encrypt_indicator.delete("all")
        color = "#00cc00" if self.key else "#999999"
        self.encrypt_indicator.create_oval(2, 2, 10, 10, fill=color, outline="")
    
    def setup_download_tab(self, parent):
        ttk.Label(parent, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.url_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.url_var, width=45).grid(row=0, column=1, padx=5, pady=3)
        self.info_button = ttk.Button(parent, text="ⓘ", width=3, command=self.get_video_info)
        self.info_button.grid(row=0, column=2, pady=3)
        
        ttk.Label(parent, text="Качество:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.quality_var = tk.StringVar(value="best")
        quality_combo = ttk.Combobox(parent, textvariable=self.quality_var, width=42,
                                      values=["best", "1080p", "720p", "480p", "audio"])
        quality_combo.grid(row=1, column=1, padx=4, pady=1)
        
        ttk.Label(parent, text="Сохранить в:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.download_dir_var = tk.StringVar(value="downloads")
        ttk.Entry(parent, textvariable=self.download_dir_var, width=45).grid(row=2, column=1, padx=5, pady=3)
        ttk.Button(parent, text="📁", width=3, command=self.select_download_dir).grid(row=2, column=2, pady=3)
        
        self.download_button = ttk.Button(parent, text="🚀 СКАЧАТЬ ВИДЕО", 
                                          command=self.start_download)
        self.download_button.grid(row=3, column=0, columnspan=3, pady=15)
        
        info_frame = ttk.LabelFrame(parent, text="Информация о видео", padding="5")
        info_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        self.video_info_text = scrolledtext.ScrolledText(info_frame, height=8, width=60, 
                                                           font=('Consolas', 9))
        self.video_info_text.pack(fill=tk.BOTH, expand=True)
        
        parent.columnconfigure(1, weight=1)
        
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
    
    def select_download_dir(self):
        dirname = filedialog.askdirectory(title="Выберите папку для сохранения видео")
        if dirname:
            self.download_dir_var.set(dirname)
    
    def get_video_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Введите URL видео!")
            return
        
        self.info_button.config(state=tk.DISABLED, text="⏳ Загрузка...")
        self.video_info_text.delete(1.0, tk.END)
        
        def fetch_info():
            if self.downloader is None:
                self.downloader = YouTubeDownloader()
            
            info = self.downloader.get_video_info(url, log_callback=lambda msg: self.log(msg))
            
            def update_ui():
                if info:
                    info_text = f"""
📹 Название: {info['title']}
⏱️ Длительность: {info.get('duration_str', 'Unknown')}
👁️ Просмотров: {info.get('views', 0):,}
👤 Автор: {info.get('uploader', 'Unknown')}
📅 Дата: {info.get('upload_date', 'Unknown')}
                    """
                    self.video_info_text.insert(1.0, info_text)
                    self.log(f"✅ Информация получена: {info['title']}")
                else:
                    self.video_info_text.insert(1.0, "Не удалось получить информацию о видео.\nПроверьте URL и подключение к интернету.")
                self.info_button.config(state=tk.NORMAL, text="ℹ️ Получить инфо")
            
            self.root.after(0, update_ui)
        
        threading.Thread(target=fetch_info, daemon=True).start()
    
    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Введите URL видео!")
            return
        
        output_dir = self.download_dir_var.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except:
                messagebox.showerror("Ошибка", f"Не удалось создать папку: {output_dir}")
                return
        
        quality = self.quality_var.get()
        
        self.download_button.config(state=tk.DISABLED, text="⏳ Скачивание...")
        self.progress_var.set(0)
        self.log(f"🚀 Начинаю скачивание: {url}")
        self.log(f"📁 Качество: {quality}")
        
        def download_thread():
            if self.downloader is None:
                self.downloader = YouTubeDownloader()
            
            result = self.downloader.download_video(
                url, output_dir, quality,
                progress_callback=lambda p: self.root.after(0, self.update_progress, p),
                log_callback=lambda msg: self.root.after(0, self.log, msg)
            )
            
            self.root.after(0, self.download_finished, result)
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def update_progress(self, percent):
        self.progress_var.set(percent)
        self.status_label.config(text=f"⏳ Прогресс: {percent:.1f}%")
        self.root.update_idletasks()
    
    def update_progress_frame(self, current, total):
        if total > 0:
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_label.config(text=f"⏳ Прогресс: {current}/{total} ({percent:.0f}%)")
            self.root.update_idletasks()
    
    def download_finished(self, result):
        self.download_button.config(state=tk.NORMAL, text="🚀 СКАЧАТЬ ВИДЕО")
        self.progress_var.set(0)
        self.status_label.config(text="✅ Готов")
        
        if result:
            self.log("✅ Видео успешно скачано!")
            messagebox.showinfo("Успех", f"Видео скачано!\n\nСохранено в: {self.download_dir_var.get()}")
        else:
            self.log("❌ Ошибка при скачивании!")
            messagebox.showerror("Ошибка", "Не удалось скачать видео!\n\nПроверьте URL и подключение к интернету.")
    
    def setup_encode_tab(self, parent):
        ttk.Label(parent, text="Исходный файл:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.encode_file_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.encode_file_var, width=45).grid(row=0, column=1, padx=5, pady=3)
        ttk.Button(parent, text="📂", width=3, command=self.select_encode_file).grid(row=0, column=2, pady=3)
        
        ttk.Label(parent, text="Выходное видео:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.output_video_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.output_video_var, width=45).grid(row=1, column=1, padx=5, pady=3)
        ttk.Button(parent, text="💾", width=3, command=self.select_output_video).grid(row=1, column=2, pady=3)
        
        destination_frame = ttk.LabelFrame(parent, text="Куда сохранить результат", padding="5")
        destination_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        self.dest_type = tk.StringVar(value="pc")
        
        radio_frame = ttk.Frame(destination_frame)
        radio_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Radiobutton(radio_frame, text="💾 Сохранить на ПК", 
                        variable=self.dest_type, value="pc",
                        command=self.on_destination_change).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Radiobutton(radio_frame, text="📤 Загрузить на YouTube", 
                        variable=self.dest_type, value="youtube",
                        command=self.on_destination_change).pack(side=tk.LEFT)
        
        self.guide_link = ttk.Label(radio_frame, text="Гайд по этой функции (ВАЖНО!!!)", 
                                    foreground="red", cursor="hand2", font=('Arial', 8, 'underline'))
        self.guide_link.bind("<Button-1>", lambda e: self.open_guide())
        self.guide_link.pack_forget()
        
        self.youtube_frame = ttk.Frame(destination_frame)
        self.youtube_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(self.youtube_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.youtube_title_var = tk.StringVar()
        ttk.Entry(self.youtube_frame, textvariable=self.youtube_title_var, width=30).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.youtube_frame, text="Приватность:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.youtube_privacy_var = tk.StringVar(value="unlisted")
        privacy_combo = ttk.Combobox(self.youtube_frame, textvariable=self.youtube_privacy_var, 
                                      values=["public", "unlisted", "private"], width=15)
        privacy_combo.grid(row=1, column=1, padx=5)
        
        self.youtube_frame.grid_remove()
        
        self.compress_frame = ttk.LabelFrame(parent, text="Сжатие 7z (максимальное)", padding="5")
        self.compress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        self.compress_checkbox = ttk.Checkbutton(self.compress_frame, text="Сжать видео в 7z архив после создания", 
                                                 variable=self.compress_after_encode)
        self.compress_checkbox.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(self.compress_frame, text="Уровень сжатия:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.level_scale = ttk.Scale(self.compress_frame, from_=0, to=9, variable=self.compression_level, 
                                     orient=tk.HORIZONTAL, length=150)
        self.level_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        self.level_label = ttk.Label(self.compress_frame, text="9 (максимум)")
        self.level_label.grid(row=1, column=2, sticky=tk.W, padx=5)
        
        def update_level_label(*args):
            level = self.compression_level.get()
            names = {0: "0 (без сжатия)", 1: "1 (быстрое)", 3: "3 (среднее)", 
                     5: "5 (нормальное)", 7: "7 (сильное)", 9: "9 (максимум)"}
            self.level_label.config(text=names.get(level, f"{level}"))
        
        self.compression_level.trace('w', update_level_label)
        update_level_label()
        
        info_frame = ttk.LabelFrame(parent, text="Информация", padding="5")
        info_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        info_text = "YTV2: 1920x1080 | 15 FPS | Блоки 8x8 | 16 цветов"
        ttk.Label(info_frame, text=info_text, font=('Arial', 8)).pack()
        
        self.encode_button = ttk.Button(parent, text="🚀 НАЧАТЬ КОДИРОВАНИЕ", 
                                        command=self.start_encode)
        self.encode_button.grid(row=5, column=0, columnspan=3, pady=10)
        
        parent.columnconfigure(1, weight=1)
    
    def select_encode_file(self):
        filename = filedialog.askopenfilename(title="Выберите файл для кодирования")
        if filename:
            self.encode_file_var.set(filename)
            default_output = os.path.splitext(os.path.basename(filename))[0] + ".mp4"
            self.output_video_var.set(default_output)
            self.youtube_title_var.set(os.path.splitext(os.path.basename(filename))[0])
            self.log(f"📄 Выбран: {os.path.basename(filename)}")
    
    def select_output_video(self):
        filename = filedialog.asksaveasfilename(title="Сохранить видео как", 
                                                defaultextension=".mp4",
                                                filetypes=[("MP4 файлы", "*.mp4")])
        if filename:
            self.output_video_var.set(filename)
    
    def on_destination_change(self):
        if self.dest_type.get() == "youtube":
            self.compress_frame.grid_remove()
            self.compress_after_encode.set(False)
            self.youtube_frame.grid()
            self.guide_link.pack(side=tk.LEFT, padx=(15, 0))
            self.log("📤 Выбрана загрузка на YouTube (сжатие 7z отключено)")
        else:
            self.compress_frame.grid()
            self.youtube_frame.grid_remove()
            self.guide_link.pack_forget()
            self.log("💾 Выбрано сохранение на ПК")
    
    def setup_decode_tab(self, parent):
        parent.columnconfigure(0, weight=0)  # левая колонка (метки)
        parent.columnconfigure(1, weight=1)  # центральная (поля ввода)
        parent.columnconfigure(2, weight=0)  # правая (кнопки)
        
        # Выбор источника
        self.decode_source = tk.StringVar(value="file")
        
        source_frame = ttk.LabelFrame(parent, text="Источник", padding="5")
        source_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))
        
        ttk.Radiobutton(source_frame, text="📁 Видео на ПК", 
                        variable=self.decode_source, value="file",
                        command=self.on_decode_source_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(source_frame, text="🌐 YouTube URL", 
                        variable=self.decode_source, value="url",
                        command=self.on_decode_source_change).pack(side=tk.LEFT, padx=5)
        
        # Поле для файла
        self.decode_file_frame = ttk.Frame(parent)
        self.decode_file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.decode_file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.decode_file_frame, text="Видео/Архив:").grid(row=0, column=0, sticky=tk.W)
        self.decode_video_var = tk.StringVar()
        self.decode_file_entry = ttk.Entry(self.decode_file_frame, textvariable=self.decode_video_var)
        self.decode_file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(self.decode_file_frame, text="📂", width=3, command=self.select_decode_video).grid(row=0, column=2)
        
        # Поле для URL
        self.decode_url_frame = ttk.Frame(parent)
        self.decode_url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.decode_url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.decode_url_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W)
        self.decode_url_var = tk.StringVar()
        self.decode_url_entry = ttk.Entry(self.decode_url_frame, textvariable=self.decode_url_var)
        self.decode_url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(self.decode_url_frame, text="📋", width=3, command=self.paste_url).grid(row=0, column=2)
        
        self.decode_url_frame.grid_remove()
        
        # Качество для YouTube
        self.decode_quality_frame = ttk.Frame(parent)
        self.decode_quality_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.decode_quality_frame, text="Качество:").pack(side=tk.LEFT)
        self.decode_quality_var = tk.StringVar(value="best")
        quality_combo = ttk.Combobox(self.decode_quality_frame, textvariable=self.decode_quality_var, 
                                      width=20, values=["best", "1080p", "720p", "480p"])
        quality_combo.pack(side=tk.LEFT, padx=5)
        
        self.decode_quality_frame.grid_remove()
        
        # Папка вывода
        ttk.Label(parent, text="Папка вывода:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=".")
        ttk.Entry(parent, textvariable=self.output_dir_var).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(parent, text="📁", width=3, command=self.select_output_dir).grid(row=3, column=2, pady=5)
        
        # Информация
        info_frame = ttk.LabelFrame(parent, text="Информация", padding="5")
        info_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        info_text = "YTV2 Decoder | Поддерживает: .mp4, .7z, YouTube URL"
        ttk.Label(info_frame, text=info_text, font=('Arial', 8)).pack()
        
        # Кнопка
        self.decode_button = ttk.Button(parent, text="🚀 НАЧАТЬ ДЕКОДИРОВАНИЕ", 
                                        command=self.start_decode)
        self.decode_button.grid(row=5, column=0, columnspan=3, pady=15)
        
        parent.columnconfigure(1, weight=1)
    
    def on_decode_source_change(self):
        if self.decode_source.get() == "file":
            self.decode_file_frame.grid()
            self.decode_url_frame.grid_remove()
            self.decode_quality_frame.grid_remove()
        else:
            self.decode_file_frame.grid_remove()
            self.decode_url_frame.grid()
            self.decode_quality_frame.grid()
    
    def paste_url(self):
        url = self.root.clipboard_get()
        if url:
            self.decode_url_var.set(url)
    
    def select_decode_video(self):
        filename = filedialog.askopenfilename(title="Выберите видео или архив",
                                              filetypes=[("Видео/Архив", "*.mp4 *.avi *.mov *.mkv *.7z")])
        if filename:
            self.decode_video_var.set(filename)
            self.log(f"📂 Выбрано: {os.path.basename(filename)}")
    
    def select_output_dir(self):
        dirname = filedialog.askdirectory(title="Выберите папку для сохранения")
        if dirname:
            self.output_dir_var.set(dirname)
    
    def setup_settings_tab(self, parent):
        key_frame = ttk.LabelFrame(parent, text="Шифрование", padding="8")
        key_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(key_frame, text="Ключ:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.new_key_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.new_key_var, width=30, show="*").grid(row=0, column=1, padx=5, pady=3)
        
        btn_frame = ttk.Frame(key_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=8)
        
        ttk.Button(btn_frame, text="💾 Сохранить", width=12, 
                  command=self.save_key).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ Удалить", width=12, 
                  command=self.delete_key).pack(side=tk.LEFT, padx=3)
        
        about_frame = ttk.LabelFrame(parent, text="О программе", padding="8")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        about_text = """YouCloud v2.0
        
Кодирование файлов в видео для YouTube
• 16 цветов (4 бита на блок)
• XOR шифрование (опционально)
• Сжатие в 7z
• Прямая загрузка на YouTube
• Прямая расшифровка файлов с YouTube
• Декодер: Поддержка YTV1 
• YTV2: 15 FPS, блоки 8x8

Оверхед (по весу): ~30x

Требования: Python 3.7+, FFmpeg, 7-Zip"""
        
        ttk.Label(about_frame, text=about_text, justify=tk.LEFT, font=('Arial', 8)).pack(anchor=tk.W)
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_encode(self):
        input_file = self.encode_file_var.get()
        output_file = self.output_video_var.get()

        if not input_file or not output_file:
            messagebox.showerror("Ошибка", "Выберите исходный файл и выходное видео!")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("Ошибка", "Исходный файл не найден!")
            return

        self.encode_button.config(state=tk.DISABLED, text="⏳ Кодирование...")
        self.progress_var.set(0)
        self.log(f"🚀 Начинаю кодирование: {os.path.basename(input_file)}")

        dest_type = self.dest_type.get()

        def encode_thread():
            try:
                encoder = YouTubeEncoder(self.key)
                encoder.encode(
                    input_file, 
                    output_file,
                    progress_callback=lambda c, t: self.root.after(0, self.update_progress_frame, c, t),
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )

                if dest_type == "youtube":
                    self.root.after(0, self.upload_to_youtube, output_file)
                else:
                    if self.compress_after_encode.get():
                        self.root.after(0, self.compress_and_cleanup, output_file)
                    else:
                        self.root.after(0, self.encode_finished, True, output_file, None)

            except Exception as e:
                self.log(f"❌ Ошибка: {e}")
                self.root.after(0, self.encode_finished, False, output_file, None)

        threading.Thread(target=encode_thread, daemon=True).start()
    
    def upload_to_youtube(self, video_file):
        self.log("\n📤 Начинаю загрузку на YouTube...")
        
        title = self.youtube_title_var.get().strip()
        if not title:
            title = os.path.splitext(os.path.basename(video_file))[0]
        
        privacy = self.youtube_privacy_var.get()
        
        def upload_thread():
            uploader = YouTubeUploader()
            success, video_id, video_url = uploader.upload(
                video_file, title, privacy,
                progress_callback=lambda p: self.root.after(0, self.update_progress, p),
                log_callback=lambda msg: self.root.after(0, self.log, msg)
            )
            
            try:
                os.remove(video_file)
                self.log(f"🗑️ Временное видео удалено")
            except:
                pass
            
            self.root.after(0, self.upload_finished, success, video_id, video_url)
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def upload_finished(self, success, video_id, video_url):
        self.encode_button.config(state=tk.NORMAL, text="🚀 НАЧАТЬ КОДИРОВАНИЕ")
        self.progress_var.set(0)
        self.status_label.config(text="✅ Готов")
        
        if success:
            self.log(f"\n🎉 ВИДЕО ЗАГРУЖЕНО НА YOUTUBE!")
            self.log(f"🔗 Ссылка: {video_url}")
            messagebox.showinfo("Успех!", 
                               f"Видео успешно загружено на YouTube!\n\n"
                               f"📺 Ссылка: {video_url}\n\n"
                               f"Приватность: {self.youtube_privacy_var.get()}")
        else:
            self.log("❌ Не удалось загрузить видео на YouTube")
            self.log("💡 Убедитесь, что настроен client_secret.json")
            messagebox.showerror("Ошибка", 
                               "Не удалось загрузить видео на YouTube!\n\n"
                               "Возможные причины:\n"
                               "1. Нет файла client_secret.json\n"
                               "2. Не авторизован аккаунт\n"
                               "3. Проблемы с интернетом\n\n"
                               "Смотрите лог для деталей.\n\n"
                               "Нажмите 'Гайд по этой функции' для инструкции.")
    
    def compress_and_cleanup(self, video_file):
        self.log(f"\n🗜️ Сжатие видео в архив (уровень {self.compression_level.get()})...")
        
        def compress_thread():
            level = self.compression_level.get()
            archive_path = ArchiveManager.compress_7z(
                video_file, 
                output_path=video_file + ".7z",
                level=level,
                log_callback=lambda msg: self.root.after(0, self.log, msg)
            )
            
            if archive_path:
                try:
                    os.remove(video_file)
                    self.log(f"🗑️ Оригинальное видео удалено (оставлен только архив)")
                except Exception as e:
                    self.log(f"⚠️ Не удалось удалить видео: {str(e)}")
            
            self.root.after(0, self.encode_finished, True, video_file, archive_path)
        
        threading.Thread(target=compress_thread, daemon=True).start()
    
    def encode_finished(self, success, video_file, archive_path):
        self.encode_button.config(state=tk.NORMAL, text="🚀 НАЧАТЬ КОДИРОВАНИЕ")
        self.progress_var.set(0)
        self.status_label.config(text="✅ Готов")
        
        if success:
            if archive_path and os.path.exists(archive_path):
                archive_size = os.path.getsize(archive_path) / 1024 / 1024
                self.log(f"✅ Архив создан: {os.path.basename(archive_path)}")
                self.log(f"📊 Размер архива: {archive_size:.2f} MB")
                messagebox.showinfo("Успех", f"Файл закодирован и сжат в архив!\n\n"
                                           f"Архив 7z: {os.path.basename(archive_path)}\n"
                                           f"Размер: {archive_size:.2f} MB")
            elif archive_path is None and self.compress_after_encode.get():
                video_size = os.path.getsize(video_file) / 1024 / 1024
                self.log(f"⚠️ Сжатие не удалось, сохранено только видео")
                self.log(f"📊 Размер видео: {video_size:.2f} MB")
                messagebox.showwarning("Предупреждение", f"Сжатие не удалось!\n\n"
                                                       f"Сохранено только видео:\n{video_file}\n"
                                                       f"Размер: {video_size:.2f} MB\n\n"
                                                       f"Установите 7-Zip для сжатия")
            else:
                video_size = os.path.getsize(video_file) / 1024 / 1024
                self.log(f"✅ Видео создано: {os.path.basename(video_file)}")
                self.log(f"📊 Размер видео: {video_size:.2f} MB")
                messagebox.showinfo("Успех", f"Видео создано!\n\n"
                                           f"Файл: {os.path.basename(video_file)}\n"
                                           f"Размер: {video_size:.2f} MB")
        else:
            self.log("❌ Ошибка при кодировании!")
            messagebox.showerror("Ошибка", "Не удалось закодировать файл!")
    
    def start_decode(self):
        output_dir = self.output_dir_var.get()
        
        if self.decode_source.get() == "file":
            input_file = self.decode_video_var.get()
            if not input_file:
                messagebox.showerror("Ошибка", "Выберите видео или архив!")
                return
            if not os.path.exists(input_file):
                messagebox.showerror("Ошибка", "Файл не найден!")
                return
            self._decode_from_file(input_file, output_dir)
        else:
            url = self.decode_url_var.get().strip()
            if not url:
                messagebox.showerror("Ошибка", "Введите YouTube URL!")
                return
            self._decode_from_url(url, output_dir)
    
    def _decode_from_file(self, input_file, output_dir):
        self.decode_button.config(state=tk.DISABLED, text="⏳ Декодирование...")
        self.progress_var.set(0)
        self.log(f"🚀 Начинаю декодирование: {os.path.basename(input_file)}")

        def process_thread():
            try:
                if input_file.lower().endswith('.7z'):
                    self.root.after(0, lambda: self.log("📦 Обнаружен 7z архив, распаковываю..."))

                    temp_extract = tempfile.mkdtemp()
                    success = ArchiveManager.decompress_7z(
                        input_file, 
                        output_dir=temp_extract,
                        log_callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                    )

                    if success:
                        video_file = None
                        for file in os.listdir(temp_extract):
                            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                                video_file = os.path.join(temp_extract, file)
                                break

                        if video_file:
                            self.root.after(0, lambda: self.log(f"🎬 Найден видеофайл: {os.path.basename(video_file)}"))
                            decoder = YouTubeDecoder(self.key)
                            output_path = decoder.decode(
                                video_file, 
                                output_dir,
                                progress_callback=lambda c, t: self.root.after(0, self.update_progress_frame, c, t),
                                log_callback=lambda msg: self.root.after(0, self.log, msg)
                            )
                            shutil.rmtree(temp_extract, ignore_errors=True)
                            self.root.after(0, lambda: self.decode_finished(True, output_path))
                        else:
                            self.root.after(0, lambda: self.log("❌ Видеофайл не найден в архиве!"))
                            self.root.after(0, lambda: self.decode_finished(False, None))
                    else:
                        self.root.after(0, lambda: self.decode_finished(False, None))
                else:
                    decoder = YouTubeDecoder(self.key)
                    output_path = decoder.decode(
                        input_file, 
                        output_dir,
                        progress_callback=lambda c, t: self.root.after(0, self.update_progress_frame, c, t),
                        log_callback=lambda msg: self.root.after(0, self.log, msg)
                    )
                    self.root.after(0, lambda: self.decode_finished(True, output_path))

            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Ошибка: {str(e)}"))
                self.root.after(0, lambda: self.decode_finished(False, None))

        threading.Thread(target=process_thread, daemon=True).start()
    
    def _decode_from_url(self, url, output_dir):
        self.decode_button.config(state=tk.DISABLED, text="⏳ Скачивание и декодирование...")
        self.progress_var.set(0)
        self.log(f"🌐 Скачиваю с YouTube: {url}")
        
        quality = self.decode_quality_var.get()
        
        def process_thread():
            temp_dir = tempfile.mkdtemp()
            try:
                if self.downloader is None:
                    self.downloader = YouTubeDownloader()
                
                video_path = self.downloader.download_video(
                    url, temp_dir, quality,
                    progress_callback=lambda p: self.root.after(0, self.update_progress, p),
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )
                
                if not video_path:
                    self.root.after(0, lambda: self.log("❌ Не удалось скачать видео"))
                    self.root.after(0, lambda: self.decode_finished(False, None))
                    return
                
                self.root.after(0, lambda: self.log(f"✅ Видео скачано, начинаю декодирование..."))
                
                decoder = YouTubeDecoder(self.key)
                output_path = decoder.decode(
                    video_path,
                    output_dir,
                    progress_callback=lambda c, t: self.root.after(0, self.update_progress_frame, c, t),
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )
                
                self.root.after(0, lambda: self.decode_finished(True, output_path))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Ошибка: {str(e)}"))
                self.root.after(0, lambda: self.decode_finished(False, None))
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def decode_finished(self, success, output_path=None):
        self.decode_button.config(state=tk.NORMAL, text="🚀 НАЧАТЬ ДЕКОДИРОВАНИЕ")
        self.progress_var.set(0)
        self.status_label.config(text="✅ Готов")
        
        if success:
            self.log("✅ Декодирование успешно завершено!")
            messagebox.showinfo("Успех", f"Файл успешно восстановлен!\n\n{os.path.basename(output_path) if output_path else ''}")
        else:
            self.log("❌ Ошибка при декодировании!")
            messagebox.showerror("Ошибка", "Не удалось декодировать файл!")
    
    def save_key(self):
        new_key = self.new_key_var.get().strip()
        if new_key:
            self.save_key_to_file(new_key)
            self.log(f"🔑 Ключ сохранен")
            self.update_encrypt_indicator()
            self.new_key_var.set("")
            messagebox.showinfo("Успех", "Ключ сохранен!")
        else:
            messagebox.showwarning("Предупреждение", "Введите ключ!")
    
    def delete_key(self):
        if messagebox.askyesno("Подтверждение", "Удалить ключ шифрования?"):
            if os.path.exists('key.txt'):
                os.remove('key.txt')
            self.key = None
            self.log("🗑️ Ключ удален")
            self.update_encrypt_indicator()
            messagebox.showinfo("Успех", "Ключ удален!")
    
    def run(self):
        self.root.mainloop()