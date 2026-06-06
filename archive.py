# archive.py - Работа с 7z архивами
import subprocess
import os
import platform

class ArchiveManager:
    @staticmethod
    def _find_7zip():
        """Находит путь к 7zip в системе"""
        system = platform.system()
        
        seven_zip_paths = []
        if system == "Windows":
            seven_zip_paths = [
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
                "7z.exe"
            ]
        else:  # Linux/Mac
            seven_zip_paths = ["7z", "7zz", "p7zip"]
        
        for path in seven_zip_paths:
            try:
                subprocess.run([path, '--help'], capture_output=True, check=True)
                return path
            except:
                continue
        return None
    
    @staticmethod
    def compress_7z(file_path, output_path=None, level=9, log_callback=None):
        """Сжимает файл в 7z архив с максимальным сжатием"""
        try:
            if output_path is None:
                output_path = file_path + ".7z"
            
            seven_zip = ArchiveManager._find_7zip()
            
            if seven_zip is None:
                if log_callback:
                    log_callback("⚠️ 7-Zip не найден! Установите 7-Zip для сжатия")
                return None
            
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
            
            seven_zip = ArchiveManager._find_7zip()
            
            if seven_zip is None:
                if log_callback:
                    log_callback("⚠️ 7-Zip не найден! Установите 7-Zip для распаковки")
                return False
            
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