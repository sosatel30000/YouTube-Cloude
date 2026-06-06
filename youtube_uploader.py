# youtube_uploader.py - Загрузка видео на YouTube
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    def __init__(self):
        self.service = None
    
    def authenticate(self, log_callback=None):
        """Авторизация в YouTube API"""
        creds = None
        
        # Проверяем сохраненный токен
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                if log_callback:
                    log_callback("✅ Найден сохраненный токен")
            except Exception as e:
                if log_callback:
                    log_callback(f"⚠️ Ошибка чтения token.json: {e}")
                if os.path.exists('token.json'):
                    os.remove('token.json')
        
        # Если токен недействителен - обновляем или создаем новый
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    if log_callback:
                        log_callback("🔄 Обновление токена...")
                    creds.refresh(Request())
                    if log_callback:
                        log_callback("✅ Токен обновлен!")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠️ Не удалось обновить токен: {e}")
                    creds = None
            
            if not creds or not creds.valid:
                # Проверяем наличие client_secret.json
                if not os.path.exists('client_secret.json'):
                    if log_callback:
                        log_callback("\n❌ Файл client_secret.json не найден!")
                        self.show_instructions(log_callback)
                    return False
                
                try:
                    if log_callback:
                        log_callback("\n🔐 Запуск авторизации...")
                        log_callback("💡 Откроется браузер для входа в Google аккаунт")
                    
                    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    if log_callback:
                        log_callback("✅ Авторизация успешна!")
                    
                    # Сохраняем токен
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                    if log_callback:
                        log_callback("💾 Токен сохранен в token.json")
                    
                except Exception as e:
                    if log_callback:
                        log_callback(f"\n❌ Ошибка авторизации: {e}")
                        log_callback("\nВозможные проблемы:")
                        log_callback("1. Неправильный файл client_secret.json")
                        log_callback("2. Не настроен экран согласия OAuth")
                        log_callback("3. Не добавлен тестовый пользователь")
                    return False
        
        try:
            self.service = build('youtube', 'v3', credentials=creds)
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Ошибка создания сервиса: {e}")
            return False
    
    def show_instructions(self, log_callback=None):
        """Показывает инструкцию по созданию client_secret.json"""
        if log_callback:
            log_callback("\n" + "="*60)
            log_callback("🔧 НАСТРОЙКА GOOGLE CLOUD CONSOLE")
            log_callback("="*60)
            log_callback("""
1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект
3. Включите YouTube Data API v3
4. Настройте экран согласия OAuth (External)
5. Создайте OAuth 2.0 Client ID (Desktop app)
6. Скачайте JSON и переименуйте в client_secret.json
7. Поместите файл в папку с программой
            """)
            log_callback("="*60)
    
    def upload(self, video_path, title, privacy_status='unlisted', 
               description="", category_id='22',
               progress_callback=None, log_callback=None):
        """Загружает видео на YouTube"""
        
        # Проверяем существование файла
        if not os.path.exists(video_path):
            if log_callback:
                log_callback(f"❌ Файл не найден: {video_path}")
            return False, None, None
        
        # Авторизуемся
        if not self.authenticate(log_callback):
            return False, None, None
        
        # Определяем размер файла
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        if log_callback:
            log_callback(f"\n📤 Загрузка: {os.path.basename(video_path)}")
            log_callback(f"📦 Размер: {file_size:.2f} MB")
            log_callback(f"📝 Название: {title}")
            log_callback(f"🔒 Приватность: {privacy_status}")
        
        # Настройка тела запроса
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'categoryId': category_id,
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = self.service.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        response = None
        last_percent = 0
        
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                if percent != last_percent:
                    if progress_callback:
                        progress_callback(percent)
                    if log_callback and (percent % 20 == 0 or percent == 100):
                        log_callback(f"⏫ Прогресс: {percent}%")
                    last_percent = percent
        
        if response and 'id' in response:
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            if log_callback:
                log_callback(f"\n✅ Видео успешно загружено!")
                log_callback(f"🔗 Ссылка: {video_url}")
            return True, video_id, video_url
        else:
            if log_callback:
                log_callback(f"\n❌ Ошибка загрузки: {response}")
            return False, None, None