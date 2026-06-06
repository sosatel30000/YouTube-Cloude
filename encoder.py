# encoder.py - Новый стандарт YTV2
import os
import math
import tempfile
import subprocess

import cv2
import numpy as np


class YouTubeEncoder:
    """YTV2 Encoder - 1920x1080, 15 FPS, блоки 8x8, 16 цветов"""
    
    def __init__(self, key=None):
        self.width = 1920
        self.height = 1080
        self.fps = 15
        
        self.block_w = 8
        self.block_h = 8
        self.spacing = 1
        
        self.marker_size = 16
        
        self.key = key
        self.use_encryption = key is not None
        
        # Палитра из 16 цветов (4 бита на блок)
        self.palette = {
            '0000': (255, 0, 0),
            '0001': (0, 255, 0),
            '0010': (0, 0, 255),
            '0011': (255, 255, 0),
            '0100': (255, 0, 255),
            '0101': (0, 255, 255),
            '0110': (255, 128, 0),
            '0111': (128, 0, 255),
            '1000': (0, 128, 128),
            '1001': (128, 128, 0),
            '1010': (128, 0, 128),
            '1011': (0, 128, 0),
            '1100': (128, 0, 0),
            '1101': (0, 0, 128),
            '1110': (192, 192, 192),
            '1111': (255, 255, 255)
        }
        
        self.blocks_x = (self.width - 2 * self.marker_size) // (self.block_w + self.spacing)
        self.blocks_y = (self.height - 2 * self.marker_size) // (self.block_h + self.spacing)
        self.blocks_per_frame = self.blocks_x * self.blocks_y
        
        self.eof_marker = "█" * 64
        self.eof_bytes = self.eof_marker.encode("utf-8")
        self.header_magic = b"YTV2|"
    
    def _xor_data(self, data: bytes) -> bytes:
        """XOR шифрование данных"""
        if not self.use_encryption:
            return data
        
        key_bytes = self.key.encode("utf-8")
        result = bytearray()
        
        for i, byte in enumerate(data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return bytes(result)
    
    def _bytes_to_bits(self, data: bytes) -> list:
        """Конвертирует байты в список 4-битных кусков"""
        bits = []
        for byte in data:
            bits.append(format(byte >> 4, '04b'))   # Старшие 4 бита
            bits.append(format(byte & 0x0F, '04b'))  # Младшие 4 бита
        return bits
    
    def _draw_markers(self, frame: np.ndarray) -> np.ndarray:
        """Рисует маркеры синхронизации по углам"""
        size = self.marker_size
        white = (255, 255, 255)
        
        cv2.rectangle(frame, (0, 0), (size, size), white, -1)
        cv2.rectangle(frame, (self.width - size, 0), (self.width, size), white, -1)
        cv2.rectangle(frame, (0, self.height - size), (size, self.height), white, -1)
        cv2.rectangle(frame, (self.width - size, self.height - size), (self.width, self.height), white, -1)
        
        return frame
    
    def _draw_block(self, frame: np.ndarray, x: int, y: int, color: tuple) -> None:
        """Рисует один блок данных"""
        px = self.marker_size + x * (self.block_w + self.spacing)
        py = self.marker_size + y * (self.block_h + self.spacing)
        
        cv2.rectangle(
            frame,
            (px, py),
            (px + self.block_w, py + self.block_h),
            color,
            -1
        )
    
    def encode(self, input_file: str, output_video: str, 
               progress_callback=None, log_callback=None) -> bool:
        """
        Кодирует файл в видео YTV2 формата
        
        Args:
            input_file: Путь к исходному файлу
            output_video: Путь для сохранения видео
            progress_callback: Функция для обновления прогресса (current, total)
            log_callback: Функция для логов
        
        Returns:
            bool: True при успехе, иначе исключение
        
        Raises:
            FileNotFoundError: Если входной файл не найден
            Exception: При ошибках кодирования
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Файл не найден: {input_file}")
        
        if log_callback:
            log_callback(f"📄 Загружаем файл: {os.path.basename(input_file)}")
        
        temp_dir = tempfile.mkdtemp(prefix="ytv2_")
        
        try:
            # Читаем исходный файл
            with open(input_file, "rb") as f:
                file_data = f.read()
            
            if log_callback:
                log_callback(f"📊 Размер: {len(file_data)} байт")
                log_callback(f"🔐 Шифрование: {'включено' if self.use_encryption else 'выключено'}")
            
            # Шифруем данные
            file_data = self._xor_data(file_data)
            
            # Формируем заголовок и полезную нагрузку
            filename = os.path.basename(input_file)
            filesize = len(file_data)
            
            header = f"YTV2|{filename}|{filesize}|".encode("utf-8")
            payload = header + file_data + self.eof_bytes
            
            # Конвертируем в 4-битные блоки
            all_bits = self._bytes_to_bits(payload)
            
            # Вычисляем необходимое количество кадров
            frames_needed = math.ceil(len(all_bits) / self.blocks_per_frame)
            
            if log_callback:
                log_callback(f"🎬 Создаём {frames_needed} кадров...")
                log_callback(f"📐 Формат: {self.width}x{self.height}, {self.fps} FPS")
            
            # Генерируем кадры
            for frame_num in range(frames_needed):
                if progress_callback:
                    progress_callback(frame_num + 1, frames_needed)
                
                # Создаем черный кадр
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                
                # Рисуем маркеры синхронизации
                frame = self._draw_markers(frame)
                
                # Определяем блоки для этого кадра
                start_idx = frame_num * self.blocks_per_frame
                end_idx = min(start_idx + self.blocks_per_frame, len(all_bits))
                frame_bits = all_bits[start_idx:end_idx]
                
                # Рисуем блоки данных
                for idx, bits in enumerate(frame_bits):
                    if idx >= self.blocks_per_frame:
                        break
                    
                    y = idx // self.blocks_x
                    x = idx % self.blocks_x
                    
                    if y >= self.blocks_y:
                        break
                    
                    color = self.palette[bits]
                    self._draw_block(frame, x, y, color)
                
                # Сохраняем кадр
                frame_file = os.path.join(temp_dir, f"frame_{frame_num:05d}.png")
                cv2.imwrite(frame_file, frame)
            
            if log_callback:
                log_callback(f"🎬 Собираем видео через FFmpeg...")
            
            # Собираем видео через FFmpeg
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-framerate", str(self.fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_video
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg ошибка: {result.stderr}")
            
            if log_callback:
                video_size = os.path.getsize(output_video) / 1024 / 1024
                log_callback(f"✅ Видео создано: {video_size:.2f} MB")
            
            return True
            
        finally:
            # Очищаем временные файлы
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)