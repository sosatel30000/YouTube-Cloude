# youtube_storage_gui.py
import cv2
import numpy as np
import os
import math
import subprocess
import tempfile
import shutil
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

class YouTubeEncoder:
    def __init__(self, key=None):
        self.width = 1920
        self.height = 1080
        self.fps = 6
        self.block_height = 16
        self.block_width = 24
        self.spacing = 4
        self.key = key
        self.use_encryption = key is not None
        
        self.colors = {
            '0000': (255, 0, 0), '0001': (0, 255, 0), '0010': (0, 0, 255),
            '0011': (255, 255, 0), '0100': (255, 0, 255), '0101': (0, 255, 255),
            '0110': (255, 128, 0), '0111': (128, 0, 255), '1000': (0, 128, 128),
            '1001': (128, 128, 0), '1010': (128, 0, 128), '1011': (0, 128, 0),
            '1100': (128, 0, 0), '1101': (0, 0, 128), '1110': (192, 192, 192),
            '1111': (255, 255, 255)
        }
        
        self.marker_size = 80
        self.blocks_x = (self.width - 2*self.marker_size) // (self.block_width + self.spacing)
        self.blocks_y = (self.height - 2*self.marker_size) // (self.block_height + self.spacing)
        self.blocks_per_region = self.blocks_x * self.blocks_y
        self.eof_marker = "█" * 64
        self.eof_bytes = self.eof_marker.encode('utf-8')
    
    def _encrypt_data(self, data):
        if not self.use_encryption:
            return data
        key_bytes = self.key.encode()
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return result
    
    def _draw_markers(self, frame):
        cv2.rectangle(frame, (0, 0), (self.marker_size, self.marker_size), (255, 255, 255), -1)
        cv2.rectangle(frame, (self.width-self.marker_size, 0), (self.width, self.marker_size), (255, 255, 255), -1)
        cv2.rectangle(frame, (0, self.height-self.marker_size), (self.marker_size, self.height), (255, 255, 255), -1)
        cv2.rectangle(frame, (self.width-self.marker_size, self.height-self.marker_size), (self.width, self.height), (255, 255, 255), -1)
        return frame
    
    def _draw_block(self, frame, x, y, color):
        x1 = self.marker_size + x * (self.block_width + self.spacing)
        y1 = self.marker_size + y * (self.block_height + self.spacing)
        x2 = x1 + self.block_width
        y2 = y1 + self.block_height
        if x2 > self.width - self.marker_size or y2 > self.height - self.marker_size:
            return False
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 1)
        return True
    
    def _bits_to_color(self, bits):
        while len(bits) < 4:
            bits = '0' + bits
        return self.colors.get(bits, (255, 0, 0))
    
    def _data_to_blocks(self, data):
        all_bits = []
        for byte in data:
            for i in range(7, -1, -1):
                all_bits.append(str((byte >> i) & 1))
        while len(all_bits) % 4 != 0:
            all_bits.append('0')
        return [''.join(all_bits[i:i+4]) for i in range(0, len(all_bits), 4)]
    
    def encode(self, input_file, output_file, progress_callback=None, log_callback=None):
        try:
            with open(input_file, 'rb') as f:
                data = f.read()
            
            if log_callback:
                log_callback(f"📄 {os.path.basename(input_file)} ({len(data)} байт)")
            
            encrypted_data = self._encrypt_data(data) if self.use_encryption else data
            header = f"FILE:{os.path.basename(input_file)}:SIZE:{len(data)}|"
            header_bytes = header.encode('latin-1')
            
            all_blocks = (self._data_to_blocks(header_bytes) + 
                         self._data_to_blocks(encrypted_data) + 
                         self._data_to_blocks(self.eof_bytes))
            
            frames_needed = math.ceil(len(all_blocks) / self.blocks_per_region) + 5
            temp_dir = tempfile.mkdtemp()
            
            for frame_num in range(frames_needed - 5):
                if progress_callback:
                    progress_callback(frame_num + 1, frames_needed)
                
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                frame = self._draw_markers(frame)
                
                start_idx = frame_num * self.blocks_per_region
                end_idx = min(start_idx + self.blocks_per_region, len(all_blocks))
                frame_blocks = all_blocks[start_idx:end_idx]
                
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x
                    x = idx % self.blocks_x
                    if y < self.blocks_y:
                        self._draw_block(frame, x, y, self._bits_to_color(bits))
                
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x
                    x = idx % self.blocks_x + self.blocks_x
                    if x < self.blocks_x * 2 and y < self.blocks_y:
                        self._draw_block(frame, x, y, self._bits_to_color(bits))
                
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x + self.blocks_y
                    x = idx % self.blocks_x
                    if x < self.blocks_x and y < self.blocks_y * 2:
                        self._draw_block(frame, x, y, self._bits_to_color(bits))
                
                cv2.imwrite(os.path.join(temp_dir, f"frame_{frame_num:05d}.png"), frame)
            
            for i in range(5):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                frame = self._draw_markers(frame)
                for y in range(self.blocks_y * 2):
                    for x in range(self.blocks_x * 2):
                        self._draw_block(frame, x, y, (255, 0, 0))
                cv2.imwrite(os.path.join(temp_dir, f"frame_{frames_needed-5+i:05d}.png"), frame)
            
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                subprocess.run([
                    'ffmpeg', '-framerate', str(self.fps),
                    '-i', os.path.join(temp_dir, 'frame_%05d.png'),
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-an', '-y', output_file
                ], check=True, capture_output=True)
            except:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_file, fourcc, self.fps, (self.width, self.height))
                for frame_num in range(frames_needed):
                    frame = cv2.imread(os.path.join(temp_dir, f"frame_{frame_num:05d}.png"))
                    if frame is not None:
                        out.write(frame)
                out.release()
            
            shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"❌ {str(e)}")
            return False


class YouTubeDecoder:
    def __init__(self, key=None):
        self.width = 1920
        self.height = 1080
        self.block_height = 16
        self.block_width = 24
        self.spacing = 4
        self.marker_size = 80
        self.key = key
        
        self.colors = {
            '0000': (255, 0, 0), '0001': (0, 255, 0), '0010': (0, 0, 255),
            '0011': (255, 255, 0), '0100': (255, 0, 255), '0101': (0, 255, 255),
            '0110': (255, 128, 0), '0111': (128, 0, 255), '1000': (0, 128, 128),
            '1001': (128, 128, 0), '1010': (128, 0, 128), '1011': (0, 128, 0),
            '1100': (128, 0, 0), '1101': (0, 0, 128), '1110': (192, 192, 192),
            '1111': (255, 255, 255)
        }
        
        self.color_values = np.array(list(self.colors.values()), dtype=np.int32)
        self.color_keys = list(self.colors.keys())
        self.color_cache = {}
        
        self.blocks_x = (self.width - 2*self.marker_size) // (self.block_width + self.spacing)
        self.blocks_y = (self.height - 2*self.marker_size) // (self.block_height + self.spacing)
        self.blocks_per_region = self.blocks_x * self.blocks_y
        
        self.block_coords = []
        for idx in range(self.blocks_per_region):
            y = idx // self.blocks_x
            x = idx % self.blocks_x
            if y < self.blocks_y:
                cx = self.marker_size + x * (self.block_width + self.spacing) + self.block_width // 2
                cy = self.marker_size + y * (self.block_height + self.spacing) + self.block_height // 2
                self.block_coords.append((cx, cy))
    
    def _decrypt_data(self, data):
        if not self.key:
            return data
        key_bytes = self.key.encode()
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return result
    
    def _color_to_bits_fast(self, color):
        color_key = (color[0], color[1], color[2])
        if color_key in self.color_cache:
            return self.color_cache[color_key]
        
        if color[0] > 200 and color[1] < 50 and color[2] < 50:
            self.color_cache[color_key] = '0000'
            return '0000'
        
        color_arr = np.array([color[0], color[1], color[2]], dtype=np.int32)
        distances = np.sum((self.color_values - color_arr) ** 2, axis=1)
        result = self.color_keys[np.argmin(distances)]
        self.color_cache[color_key] = result
        return result
    
    def decode_frame_fast(self, frame):
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
        
        blocks = []
        for cx, cy in self.block_coords:
            if cx < frame.shape[1] and cy < frame.shape[0]:
                blocks.append(self._color_to_bits_fast(frame[cy, cx]))
            else:
                blocks.append('0000')
        return blocks
    
    def _blocks_to_bytes(self, blocks):
        all_bits = ''.join(blocks)
        bytes_data = bytearray()
        for i in range(0, len(all_bits) - 7, 8):
            byte_str = all_bits[i:i+8]
            if len(byte_str) == 8:
                try:
                    bytes_data.append(int(byte_str, 2))
                except:
                    bytes_data.append(0)
        return bytes_data
    
    def decode(self, video_file, output_dir='.', progress_callback=None, log_callback=None):
        try:
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                return False
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            all_blocks = []
            
            for frame_num in range(total_frames):
                if progress_callback:
                    progress_callback(frame_num + 1, total_frames)
                
                ret, frame = cap.read()
                if not ret:
                    break
                all_blocks.extend(self.decode_frame_fast(frame))
            
            cap.release()
            bytes_data = self._blocks_to_bytes(all_blocks)
            
            # Поиск EOF маркера
            eof_bytes = b'\xe2\x96\x88' * 64
            eof_pos = bytes_data.find(eof_bytes)
            if eof_pos > 0:
                bytes_data = bytes_data[:eof_pos]
            
            # Поиск заголовка
            data_str = bytes_data[:1000].decode('latin-1', errors='ignore')
            match = re.search(r'FILE:([^:]+):SIZE:(\d+)\|', data_str)
            
            if match:
                filename = match.group(1)
                filesize = int(match.group(2))
                header_bytes = match.group(0).encode('latin-1')
                header_pos = bytes_data.find(header_bytes)
                
                if header_pos >= 0:
                    encrypted_data = bytes_data[header_pos + len(header_bytes):header_pos + len(header_bytes) + filesize]
                    file_data = self._decrypt_data(encrypted_data)
                    
                    output_path = os.path.join(output_dir, filename)
                    counter = 1
                    base, ext = os.path.splitext(filename)
                    while os.path.exists(output_path):
                        output_path = os.path.join(output_dir, f"{base}_{counter}{ext}")
                        counter += 1
                    
                    with open(output_path, 'wb') as f:
                        f.write(file_data)
                    
                    if log_callback:
                        log_callback(f"✅ {filename} ({len(file_data)} байт)")
                    return True
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"❌ {str(e)}")
            return False


class ArchiveManager:
    @staticmethod
    def compress_7z(file_path, output_path=None, level=9, log_callback=None):
        """Сжимает файл в 7z архив с максимальным сжатием"""
        try:
            if output_path is None:
                output_path = file_path + ".7z"
            
            # Проверяем наличие 7z в системе
            import platform
            system = platform.system()
            
            # Пытаемся найти 7z
            seven_zip_paths = []
            if system == "Windows":
                seven_zip_paths = [
                    r"C:\Program Files\7-Zip\7z.exe",
                    r"C:\Program Files (x86)\7-Zip\7z.exe",
                    "7z.exe"
                ]
            else:  # Linux/Mac
                seven_zip_paths = ["7z", "7zz", "p7zip"]
            
            seven_zip = None
            for path in seven_zip_paths:
                try:
                    subprocess.run([path, '--help'], capture_output=True, check=True)
                    seven_zip = path
                    break
                except:
                    continue
            
            if seven_zip is None:
                if log_callback:
                    log_callback("⚠️ 7-Zip не найден! Установите 7-Zip для сжатия")
                return None
            
            # Сжимаем
            cmd = [seven_zip, 'a', f'-mx={level}', output_path, file_path]
            
            if log_callback:
                log_callback(f"🗜️ Сжатие в 7z (уровень {level})...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                original_size = os.path.getsize(file_path)
                compressed_size = os.path.getsize(output_path)
                ratio = (compressed_size / original_size) * 100 if original_size > 0 else 0
                
                if log_callback:
                    log_callback(f"✅ Сжато: {original_size/1024/1024:.2f} MB → {compressed_size/1024/1024:.2f} MB ({ratio:.1f}%)")
                return output_path
            else:
                if log_callback:
                    log_callback(f"❌ Ошибка сжатия: {result.stderr}")
                return None
                
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Ошибка сжатия: {str(e)}")
            return None
    
    @staticmethod
    def decompress_7z(archive_path, output_dir=None, log_callback=None):
        """Распаковывает 7z архив"""
        try:
            if output_dir is None:
                output_dir = os.path.dirname(archive_path)
            
            import platform
            system = platform.system()
            
            seven_zip_paths = []
            if system == "Windows":
                seven_zip_paths = [
                    r"C:\Program Files\7-Zip\7z.exe",
                    r"C:\Program Files (x86)\7-Zip\7z.exe",
                    "7z.exe"
                ]
            else:
                seven_zip_paths = ["7z", "7zz", "p7zip"]
            
            seven_zip = None
            for path in seven_zip_paths:
                try:
                    subprocess.run([path, '--help'], capture_output=True, check=True)
                    seven_zip = path
                    break
                except:
                    continue
            
            if seven_zip is None:
                if log_callback:
                    log_callback("⚠️ 7-Zip не найден! Установите 7-Zip для распаковки")
                return None
            
            cmd = [seven_zip, 'x', archive_path, f'-o{output_dir}', '-y']
            
            if log_callback:
                log_callback(f"📦 Распаковка архива...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if log_callback:
                    log_callback(f"✅ Архив распакован в: {output_dir}")
                return True
            else:
                if log_callback:
                    log_callback(f"❌ Ошибка распаковки: {result.stderr}")
                return False
                
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Ошибка распаковки: {str(e)}")
            return False


class YouTubeStorageGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube File Storage")
        self.root.geometry("620x600")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')
        
        self.key = self.read_key_from_file()
        self.compress_after_encode = tk.BooleanVar(value=True)
        self.compression_level = tk.IntVar(value=9)
        
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
    
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(title_frame, text="🎥 YouTube File Storage", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        self.encrypt_indicator = tk.Canvas(title_frame, width=12, height=12, bg='#f0f0f0', highlightthickness=0)
        self.encrypt_indicator.pack(side=tk.RIGHT, padx=5)
        self.update_encrypt_indicator()
        
        # Ноутбук
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        encode_tab = ttk.Frame(notebook, padding="8")
        notebook.add(encode_tab, text="📤 Кодировать")
        self.setup_encode_tab(encode_tab)
        
        decode_tab = ttk.Frame(notebook, padding="8")
        notebook.add(decode_tab, text="📥 Декодировать")
        self.setup_decode_tab(decode_tab)
        
        settings_tab = ttk.Frame(notebook, padding="8")
        notebook.add(settings_tab, text="⚙️ Настройки")
        self.setup_settings_tab(settings_tab)
        
        # Прогресс-бар
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(main_frame, text="✅ Готов", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(0, 5))
        
        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding="3")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70, 
                                                   font=('Consolas', 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log("=" * 50)
        self.log("🎬 Программа запущена")
        self.log(f"🔐 Шифрование: {'Включено' if self.key else 'Выключено'}")
        self.log(f"🗜️ Сжатие 7z: {'Включено' if self.compress_after_encode.get() else 'Выключено'} (уровень {self.compression_level.get()})")
        self.log("=" * 50)
    
    def update_encrypt_indicator(self):
        self.encrypt_indicator.delete("all")
        color = "#00cc00" if self.key else "#999999"
        self.encrypt_indicator.create_oval(2, 2, 10, 10, fill=color, outline="")
    
    def setup_encode_tab(self, parent):
        # Исходный файл
        ttk.Label(parent, text="Исходный файл:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.encode_file_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.encode_file_var, width=45).grid(row=0, column=1, padx=5, pady=3)
        ttk.Button(parent, text="📂", width=3, command=self.select_encode_file).grid(row=0, column=2, pady=3)
        
        # Выходное видео
        ttk.Label(parent, text="Выходное видео:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.output_video_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.output_video_var, width=45).grid(row=1, column=1, padx=5, pady=3)
        ttk.Button(parent, text="💾", width=3, command=self.select_output_video).grid(row=1, column=2, pady=3)
        
        # Опции сжатия
        compress_frame = ttk.LabelFrame(parent, text="Сжатие 7z (максимальное)", padding="5")
        compress_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        ttk.Checkbutton(compress_frame, text="Сжать видео в 7z архив после создания", 
                       variable=self.compress_after_encode).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(compress_frame, text="Уровень сжатия:").grid(row=1, column=0, sticky=tk.W, pady=3)
        level_scale = ttk.Scale(compress_frame, from_=0, to=9, variable=self.compression_level, 
                                orient=tk.HORIZONTAL, length=150)
        level_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        self.level_label = ttk.Label(compress_frame, text="9 (максимум)")
        self.level_label.grid(row=1, column=2, sticky=tk.W, padx=5)
        
        def update_level_label(*args):
            level = self.compression_level.get()
            names = {0: "0 (без сжатия)", 1: "1 (быстрое)", 3: "3 (среднее)", 
                     5: "5 (нормальное)", 7: "7 (сильное)", 9: "9 (максимум)"}
            self.level_label.config(text=names.get(level, f"{level}"))
        
        self.compression_level.trace('w', update_level_label)
        update_level_label()
        
        # Информация
        info_frame = ttk.LabelFrame(parent, text="Информация", padding="5")
        info_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        info_text = "1920x1080 | 6 FPS | Блоки 24x16 | Тройная защита"
        ttk.Label(info_frame, text=info_text, font=('Arial', 8)).pack()
        
        # Кнопка старта
        self.encode_button = ttk.Button(parent, text="🚀 НАЧАТЬ КОДИРОВАНИЕ", 
                                        command=self.start_encode)
        self.encode_button.grid(row=4, column=0, columnspan=3, pady=10)
        
        parent.columnconfigure(1, weight=1)
    
    def setup_decode_tab(self, parent):
        # Видео/Архив файл
        ttk.Label(parent, text="Видео/Архив:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.decode_video_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.decode_video_var, width=45).grid(row=0, column=1, padx=5, pady=3)
        ttk.Button(parent, text="📂", width=3, command=self.select_decode_video).grid(row=0, column=2, pady=3)
        
        # Папка вывода
        ttk.Label(parent, text="Папка вывода:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.output_dir_var = tk.StringVar(value=".")
        ttk.Entry(parent, textvariable=self.output_dir_var, width=45).grid(row=1, column=1, padx=5, pady=3)
        ttk.Button(parent, text="📁", width=3, command=self.select_output_dir).grid(row=1, column=2, pady=3)
        
        # Информация
        info_frame = ttk.LabelFrame(parent, text="Информация", padding="5")
        info_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        
        info_text = "Автоопределение формата | Поддержка .mp4 и .7z"
        ttk.Label(info_frame, text=info_text, font=('Arial', 8)).pack()
        
        # Кнопка старта
        self.decode_button = ttk.Button(parent, text="🚀 НАЧАТЬ ДЕКОДИРОВАНИЕ", 
                                        command=self.start_decode)
        self.decode_button.grid(row=3, column=0, columnspan=3, pady=10)
        
        parent.columnconfigure(1, weight=1)
    
    def setup_settings_tab(self, parent):
        # Ключ шифрования
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
        
        # О программе
        about_frame = ttk.LabelFrame(parent, text="О программе", padding="8")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        about_text = """YouTube File Storage v1.0
        
Кодирование файлов в видео для YouTube
• 16 цветов (4 бита на блок)
• 3 резервные области для надежности
• XOR шифрование (опционально)
• Сжатие в 7z (уровень 9 - максимальное)
• Оптимизировано для YouTube (6 FPS)

Требования: Python 3.7+, OpenCV, NumPy, 7-Zip"""
        
        ttk.Label(about_frame, text=about_text, justify=tk.LEFT, font=('Arial', 8)).pack(anchor=tk.W)
    
    def select_encode_file(self):
        filename = filedialog.askopenfilename(title="Выберите файл для кодирования")
        if filename:
            self.encode_file_var.set(filename)
            default_output = os.path.splitext(os.path.basename(filename))[0] + ".mp4"
            self.output_video_var.set(default_output)
            self.log(f"📄 Выбран: {os.path.basename(filename)}")
    
    def select_output_video(self):
        filename = filedialog.asksaveasfilename(title="Сохранить видео как", 
                                                defaultextension=".mp4",
                                                filetypes=[("MP4 файлы", "*.mp4")])
        if filename:
            self.output_video_var.set(filename)
    
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
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, current, total):
        if total > 0:
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_label.config(text=f"⏳ Прогресс: {current}/{total} ({percent:.0f}%)")
            self.root.update_idletasks()
    
    def start_encode(self):
        input_file = self.encode_file_var.get()
        output_file = self.output_video_var.get()
        
        if not input_file or not output_file:
            messagebox.showerror("Ошибка", "Выберите исходный файл и укажите выходное видео!")
            return
        if not os.path.exists(input_file):
            messagebox.showerror("Ошибка", "Исходный файл не найден!")
            return
        
        self.encode_button.config(state=tk.DISABLED, text="⏳ Кодирование...")
        self.progress_var.set(0)
        self.log(f"🚀 Начинаю кодирование: {os.path.basename(input_file)}")
        
        def encode_thread():
            encoder = YouTubeEncoder(self.key)
            success = encoder.encode(
                input_file, output_file,
                progress_callback=lambda c, t: self.root.after(0, self.update_progress, c, t),
                log_callback=lambda msg: self.root.after(0, self.log, msg)
            )
            
            if success and self.compress_after_encode.get():
                self.root.after(0, self.compress_and_cleanup, output_file)
            else:
                self.root.after(0, self.encode_finished, success, output_file, None)
        
        threading.Thread(target=encode_thread, daemon=True).start()
    
    def compress_and_cleanup(self, video_file):
        """Сжимает видео в архив и удаляет оригинал"""
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
                # Удаляем оригинальное видео
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
                # Показываем только архив
                archive_size = os.path.getsize(archive_path) / 1024 / 1024
                self.log(f"✅ Архив создан: {os.path.basename(archive_path)}")
                self.log(f"📊 Размер архива: {archive_size:.2f} MB")
                messagebox.showinfo("Успех", f"Файл закодирован и сжат в архив!\n\n"
                                           f"Архив 7z: {os.path.basename(archive_path)}\n"
                                           f"Размер: {archive_size:.2f} MB")
            elif archive_path is None and self.compress_after_encode.get():
                # Сжатие не удалось, но видео есть
                video_size = os.path.getsize(video_file) / 1024 / 1024
                self.log(f"⚠️ Сжатие не удалось, сохранено только видео")
                self.log(f"📊 Размер видео: {video_size:.2f} MB")
                messagebox.showwarning("Предупреждение", f"Сжатие не удалось!\n\n"
                                                       f"Сохранено только видео:\n{video_file}\n"
                                                       f"Размер: {video_size:.2f} MB\n\n"
                                                       f"Установите 7-Zip для сжатия")
            else:
                # Без сжатия
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
        input_file = self.decode_video_var.get()
        output_dir = self.output_dir_var.get()
        
        if not input_file:
            messagebox.showerror("Ошибка", "Выберите видео или архив!")
            return
        if not os.path.exists(input_file):
            messagebox.showerror("Ошибка", "Файл не найден!")
            return
        
        self.decode_button.config(state=tk.DISABLED, text="⏳ Декодирование...")
        self.progress_var.set(0)
        self.log(f"🚀 Начинаю обработку: {os.path.basename(input_file)}")
        
        def process_thread():
            # Проверяем, архив ли это
            if input_file.lower().endswith('.7z'):
                self.root.after(0, self.log, "📦 Обнаружен 7z архив, распаковываю...")
                
                # Распаковываем во временную папку
                temp_extract = tempfile.mkdtemp()
                success = ArchiveManager.decompress_7z(
                    input_file, 
                    output_dir=temp_extract,
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )
                
                if success:
                    # Ищем видео файл в распакованном
                    video_file = None
                    for file in os.listdir(temp_extract):
                        if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                            video_file = os.path.join(temp_extract, file)
                            break
                    
                    if video_file:
                        self.root.after(0, self.log, f"🎬 Найден видеофайл: {os.path.basename(video_file)}")
                        decoder = YouTubeDecoder(self.key)
                        decode_success = decoder.decode(
                            video_file, output_dir,
                            progress_callback=lambda c, t: self.root.after(0, self.update_progress, c, t),
                            log_callback=lambda msg: self.root.after(0, self.log, msg)
                        )
                        shutil.rmtree(temp_extract, ignore_errors=True)
                        self.root.after(0, self.decode_finished, decode_success)
                    else:
                        self.root.after(0, self.log, "❌ Видеофайл не найден в архиве!")
                        self.root.after(0, self.decode_finished, False)
                else:
                    self.root.after(0, self.decode_finished, False)
            else:
                # Обычное видео
                decoder = YouTubeDecoder(self.key)
                success = decoder.decode(
                    input_file, output_dir,
                    progress_callback=lambda c, t: self.root.after(0, self.update_progress, c, t),
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )
                self.root.after(0, self.decode_finished, success)
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def decode_finished(self, success):
        self.decode_button.config(state=tk.NORMAL, text="🚀 НАЧАТЬ ДЕКОДИРОВАНИЕ")
        self.progress_var.set(0)
        self.status_label.config(text="✅ Готов")
        
        if success:
            self.log("✅ Декодирование успешно завершено!")
            messagebox.showinfo("Успех", "Файл успешно восстановлен!")
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


if __name__ == "__main__":
    app = YouTubeStorageGUI()
    app.run()
