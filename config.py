# config.py
import os
from dotenv import load_dotenv

# .env faylını yüklə (yerli inkişaf üçün)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") # Bu sətri də yoxlayın, düzgün adlı dəyişəndən oxuduğundan əmin olun
ADMIN_ID = int(os.getenv("ADMIN_ID")) # Düzgün ətraf mühit dəyişəni adı olaraq "ADMIN_ID" istifadə edin
