# downloader.py - Скачивание видео с YouTube
import subprocess
import os
import re
import sys
import tempfile
import shutil
import time

class YouTubeDownloader:
    def __init__(self):
        self.ytdlp_path = self._get_ytdlp_path()
    
    def _get_ytdlp_path(self):
        """Находит yt-dlp.exe в папке с программой"""
        # Путь к папке, где находится текущий скрипт/executable
        if getattr(sys, 'frozen', False):
            # Запущено как exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Запущено как скрипт
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Ищем yt-dlp.exe
        possible_paths = [
            os.path.join(base_path, 'yt-dlp.exe'),
            os.path.join(base_path, 'bin', 'yt-dlp.exe'),
            'yt-dlp.exe',  # В PATH
            'yt-dlp',      # В PATH (Linux/Mac)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Если не нашли, пробуем через which
        which_path = shutil.which('yt-dlp')
        if which_path:
            return which_path
        
        return None
    
    def is_available(self, log_callback=None):
        """Проверяет доступность yt-dlp"""
        if not self.ytdlp_path:
            if log_callback:
                log_callback("❌ yt-dlp не найден!")
                log_callback("📁 Положите yt-dlp.exe в папку с программой")
            return False
        
        try:
            result = subprocess.run([self.ytdlp_path, '--version'], 
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True
        except:
            pass
        
        return False
    
    def get_video_info(self, url, log_callback=None):
        """Получает информацию о видео"""
        if not self.is_available(log_callback):
            return None
        
        try:
            cmd = [self.ytdlp_path, '--dump-json', '--skip-download', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                duration_min = data.get('duration', 0) // 60
                duration_sec = data.get('duration', 0) % 60
                
                info = {
                    'title': data.get('title', 'Unknown'),
                    'duration': data.get('duration', 0),
                    'duration_str': f"{duration_min}:{duration_sec:02d}",
                    'uploader': data.get('uploader', 'Unknown'),
                    'views': data.get('view_count', 0),
                    'upload_date': data.get('upload_date', 'Unknown')
                }
                
                if log_callback:
                    log_callback(f"📺 {info['title'][:50]}...")
                    log_callback(f"👤 {info['uploader']} | ⏱️ {info['duration_str']} | 👁️ {info['views']:,}")
                
                return info
            else:
                if log_callback:
                    log_callback(f"❌ Ошибка: {result.stderr[:200]}")
                return None
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Ошибка: {str(e)}")
            return None
    
    def download_video(self, url, output_path='.', quality='best', 
                       progress_callback=None, log_callback=None):
        """Самая простая версия - без всяких наворотов"""
        if not self.is_available(log_callback):
            return False
        
        try:
            os.makedirs(output_path, exist_ok=True)
            
            # Минимальная команда
            cmd = [
                self.ytdlp_path,
                url,
                '-o', os.path.join(output_path, '%(title)s.%(ext)s')
                
            ]
            
            if log_callback:
                log_callback(f"⬇️ Скачивание...")
            
            # Просто запускаем и ждем
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Ищем файл
                for file in os.listdir(output_path):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.mp3')):
                        file_path = os.path.join(output_path, file)
                        if log_callback:
                            log_callback(f"✅ Скачано: {file}")
                        return file_path
                return True
            else:
                # Показываем ошибку
                error_msg = result.stderr[:300] if result.stderr else "Неизвестная ошибка"
                if log_callback:
                    log_callback(f"❌ {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback(f"❌ Таймаут")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"❌ {str(e)}")
            return False
