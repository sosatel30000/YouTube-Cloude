# decoder.py - Новый стандарт YTV2 с поддержкой legacy
import os
import cv2
import numpy as np


class LegacyYTV1Decoder:
    """Декодер для старых видео (YTV1)"""
    
    def __init__(self, key=None):
        self.width = 1920
        self.height = 1080
        self.block_w = 24
        self.block_h = 16
        self.spacing = 4
        self.marker_size = 80
        self.key = key
        
        self.palette = {
            (255, 0, 0): '0000', (0, 255, 0): '0001', (0, 0, 255): '0010',
            (255, 255, 0): '0011', (255, 0, 255): '0100', (0, 255, 255): '0101',
            (255, 128, 0): '0110', (128, 0, 255): '0111', (0, 128, 128): '1000',
            (128, 128, 0): '1001', (128, 0, 128): '1010', (0, 128, 0): '1011',
            (128, 0, 0): '1100', (0, 0, 128): '1101', (192, 192, 192): '1110',
            (255, 255, 255): '1111'
        }
        
        self.palette_values = np.array(list(self.palette.keys()), dtype=np.int32)
        self.palette_bits = list(self.palette.values())
        
        self.blocks_x = (self.width - 2 * self.marker_size) // (self.block_w + self.spacing)
        self.blocks_y = (self.height - 2 * self.marker_size) // (self.block_h + self.spacing)
        
        self._precompute_coords()
    
    def _precompute_coords(self):
        self.block_centers = []
        blocks_per_frame = self.blocks_x * self.blocks_y
        
        for idx in range(blocks_per_frame):
            y = idx // self.blocks_x
            x = idx % self.blocks_x
            cx = self.marker_size + x * (self.block_w + self.spacing) + self.block_w // 2
            cy = self.marker_size + y * (self.block_h + self.spacing) + self.block_h // 2
            if cx < self.width and cy < self.height:
                self.block_centers.append((cx, cy))
    
    def _xor_data(self, data):
        if not self.key:
            return data
        key_bytes = self.key.encode('utf-8')
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return result
    
    def _color_to_bits(self, color):
        color_arr = np.array([color[0], color[1], color[2]], dtype=np.int32)
        distances = np.sum((self.palette_values - color_arr) ** 2, axis=1)
        return self.palette_bits[np.argmin(distances)]
    
    def decode_frame(self, frame):
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        blocks = []
        for cx, cy in self.block_centers:
            if 0 <= cx < frame.shape[1] and 0 <= cy < frame.shape[0]:
                color = frame[cy, cx]
                blocks.append(self._color_to_bits(color))
            else:
                blocks.append('0000')
        return blocks
    
    def decode(self, video_path, output_dir, progress_callback=None, log_callback=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Не удалось открыть видео")
        
        try:
            all_bits = []
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            for frame_num in range(frame_count):
                if progress_callback:
                    progress_callback(frame_num + 1, frame_count)
                
                ret, frame = cap.read()
                if not ret:
                    break
                all_bits.extend(self.decode_frame(frame))
            
            # Конвертируем биты в байты
            all_bits_str = ''.join(all_bits)
            raw_bytes = bytearray()
            for i in range(0, len(all_bits_str) - 7, 8):
                byte_str = all_bits_str[i:i+8]
                if len(byte_str) == 8:
                    raw_bytes.append(int(byte_str, 2))
            
            raw_bytes = bytes(raw_bytes)
            
            # Ищем заголовок FILE:name:SIZE:size|
            header_pattern = b'FILE:'
            header_pos = raw_bytes.find(header_pattern)
            
            if header_pos == -1:
                raise Exception("Не найден заголовок в видео")
            
            remaining = raw_bytes[header_pos:]
            end_pos = remaining.find(b'|')
            if end_pos == -1:
                raise Exception("Не найден конец заголовка")
            
            header = remaining[:end_pos]
            header_str = header.decode('latin-1')
            parts = header_str.split(':')
            
            if len(parts) < 4 or parts[0] != 'FILE' or parts[2] != 'SIZE':
                raise Exception("Неверный формат заголовка")
            
            filename = parts[1]
            filesize = int(parts[3])
            encrypted_data = remaining[end_pos + 1:end_pos + 1 + filesize]
            
            # Расшифровываем
            file_data = self._xor_data(encrypted_data)
            
            # Сохраняем
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            counter = 1
            base, ext = os.path.splitext(output_path)
            while os.path.exists(output_path):
                output_path = f"{base}_{counter}{ext}"
                counter += 1
            
            with open(output_path, "wb") as f:
                f.write(file_data)
            
            return output_path
            
        finally:
            cap.release()


class YouTubeDecoder:
    """YTV2 Decoder - поддерживает новый и старый форматы"""
    
    def __init__(self, key=None):
        self.width = 1920
        self.height = 1080
        self.block_w = 8
        self.block_h = 8
        self.spacing = 1
        self.marker_size = 16
        self.key = key
        self.use_encryption = key is not None
        
        self.palette = {
            (255, 0, 0): '0000', (0, 255, 0): '0001', (0, 0, 255): '0010',
            (255, 255, 0): '0011', (255, 0, 255): '0100', (0, 255, 255): '0101',
            (255, 128, 0): '0110', (128, 0, 255): '0111', (0, 128, 128): '1000',
            (128, 128, 0): '1001', (128, 0, 128): '1010', (0, 128, 0): '1011',
            (128, 0, 0): '1100', (0, 0, 128): '1101', (192, 192, 192): '1110',
            (255, 255, 255): '1111'
        }
        
        self.palette_values = np.array(list(self.palette.keys()), dtype=np.int32)
        self.palette_bits = list(self.palette.values())
        
        self.blocks_x = (self.width - 2 * self.marker_size) // (self.block_w + self.spacing)
        self.blocks_y = (self.height - 2 * self.marker_size) // (self.block_h + self.spacing)
        self.blocks_per_frame = self.blocks_x * self.blocks_y
        
        self.eof_marker = "█" * 64
        self.eof_bytes = self.eof_marker.encode("utf-8")
        self.header_magic = b"YTV2|"
        
        self._precompute_coords()
    
    def _precompute_coords(self):
        self.block_centers = []
        for idx in range(self.blocks_per_frame):
            y = idx // self.blocks_x
            x = idx % self.blocks_x
            cx = self.marker_size + x * (self.block_w + self.spacing) + self.block_w // 2
            cy = self.marker_size + y * (self.block_h + self.spacing) + self.block_h // 2
            self.block_centers.append((cx, cy))
    
    def _xor_data(self, data):
        if not self.use_encryption:
            return data
        key_bytes = self.key.encode("utf-8")
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(result)
    
    def _color_to_bits(self, color):
        color = color.flatten()[:3].astype(np.int32)
        distances = np.sum((self.palette_values - color) ** 2, axis=1)
        return self.palette_bits[np.argmin(distances)]
    
    def _bits_to_bytes(self, bits):
        result = bytearray()
        for i in range(0, len(bits), 2):
            if i + 1 < len(bits):
                byte_val = (int(bits[i], 2) << 4) | int(bits[i + 1], 2)
                result.append(byte_val)
        return bytes(result)
    
    def decode_frame(self, frame):
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        
        blocks = []
        for cx, cy in self.block_centers:
            x1 = max(0, cx - 2)
            y1 = max(0, cy - 2)
            x2 = min(self.width, cx + 3)
            y2 = min(self.height, cy + 3)
            region = frame[y1:y2, x1:x2]
            avg_color = region.mean(axis=(0, 1))
            blocks.append(self._color_to_bits(avg_color))
        return blocks
    
    def decode(self, input_video: str, output_dir: str,
               progress_callback=None, log_callback=None) -> str:
        """Декодирует видео - автоматически определяет формат"""
        
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Видео не найдено: {input_video}")
        
        # Пробуем определить формат по первому кадру
        cap = cv2.VideoCapture(input_video)
        ret, first_frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("Не удалось прочитать видео")
        
        # Определяем формат по размеру маркеров
        # Ищем белые квадраты по углам
        h, w = first_frame.shape[:2]
        marker_candidates = [80, 64, 48, 32, 16, 8]
        
        detected_marker = None
        for marker in marker_candidates:
            # Проверяем угол (0,0) на наличие белого квадрата
            roi = first_frame[0:marker, 0:marker]
            avg = roi.mean()
            if avg > 200:  # Почти белый
                detected_marker = marker
                break
        
        if log_callback:
            log_callback(f"🔍 Определён размер маркера: {detected_marker}")
        
        # Если маркер 80 - это legacy YTV1
        if detected_marker == 80:
            if log_callback:
                log_callback(f"📼 Обнаружено старое видео (YTV1), использую legacy декодер...")
            
            legacy_decoder = LegacyYTV1Decoder(self.key)
            return legacy_decoder.decode(input_video, output_dir, progress_callback, log_callback)
        
        # Иначе используем новый декодер
        if log_callback:
            log_callback(f"🎬 Обнаружено новое видео (YTV2)")
        
        cap = cv2.VideoCapture(input_video)
        if not cap.isOpened():
            raise Exception(f"Не удалось открыть видео: {input_video}")
        
        try:
            all_bits = []
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if log_callback:
                log_callback(f"📊 Всего кадров: {frame_count}")
            
            for frame_num in range(frame_count):
                if progress_callback:
                    progress_callback(frame_num + 1, frame_count)
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_bits = self.decode_frame(frame)
                all_bits.extend(frame_bits)
            
            if log_callback:
                log_callback(f"🔧 Конвертируем биты в байты...")
            
            raw_bytes = self._bits_to_bytes(all_bits)
            
            eof_pos = raw_bytes.find(self.eof_bytes)
            if eof_pos != -1:
                raw_bytes = raw_bytes[:eof_pos]
            
            if not raw_bytes.startswith(self.header_magic):
                raise Exception("Неверный формат YTV2 видео")
            
            parts = raw_bytes.split(b"|", 3)
            if len(parts) < 4:
                raise Exception("Неверный формат заголовка")
            
            filename = parts[1].decode("utf-8")
            filesize = int(parts[2].decode("utf-8"))
            encrypted_data = parts[3][:filesize]
            
            if log_callback:
                log_callback(f"📁 Файл: {filename}, размер: {filesize} байт")
            
            file_data = self._xor_data(encrypted_data)
            
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            counter = 1
            base, ext = os.path.splitext(output_path)
            while os.path.exists(output_path):
                output_path = f"{base}_{counter}{ext}"
                counter += 1
            
            with open(output_path, "wb") as f:
                f.write(file_data)
            
            if log_callback:
                file_size_mb = len(file_data) / 1024 / 1024
                log_callback(f"✅ Файл восстановлен: {os.path.basename(output_path)} ({file_size_mb:.2f} MB)")
            
            return output_path
            
        finally:
            cap.release()