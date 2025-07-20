import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import config
import database

# Logları aktivləşdir
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Botun vəziyyətləri (State machine üçün sadə yanaşma)
USER_STATES = {} # {user_id: current_state}
AWAITING_LINK = 1
AWAITING_RECEIPT = 2
AWAITING_ADMIN_REPLY = 3 # İstifadəçi adminə mesaj yazır
AWAITING_ADMIN_PRICE_CHANGE_SERVICE = 4
AWAITING_ADMIN_PRICE_CHANGE_AMOUNT = 5

# --- Köməkçi funksiyalar ---
def get_main_menu_keyboard():
    """Əsas menyu üçün Reply Keyboard yaradır."""
    keyboard = [
        [KeyboardButton("Balans artır")],
        [KeyboardButton("Balansa baxmaq")],
        [KeyboardButton("Xidmətlər")],
        [KeyboardButton("Adminlə əlaqə")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_services_menu_keyboard():
    """Xidmətlər menyusu üçün Inline Keyboard yaradır."""
    keyboard = [
        [InlineKeyboardButton("Tiktok", callback_data="services_tiktok")],
        [InlineKeyboardButton("Instagram", callback_data="services_instagram")],
        [InlineKeyboardButton("Telegram", callback_data="services_telegram")],
        [InlineKeyboardButton("Geri", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Link təsdiqləmə üçün köməkçi funksiya
def is_valid_url(url: str) -> bool:
    """Telegram, Instagram, Tiktok URL-i olub-olmadığını yoxlayır."""
    regex = re.compile(
        r'^(https?://)?(www\.)?(telegram\.me/|t\.me/|instagram\.com/|tiktok\.com/)'
        r'[a-zA-Z0-9.\-/?&=#_]*$'
    )
    return re.match(regex, url) is not None

# --- Xəta idarəçiliyi ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botda baş verən bütün xətaları idarə edir."""
    logger.error("Update %s caused error %s", update, context.error)
    try:
        if update.effective_chat.id == config.ADMIN_ID:
            await context.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=f"Botda xəta baş verdi:\n\n`{context.error}`\n\n"
                     f"Update: `{update}`",
                parse_mode="Markdown"
            )
        else:
            await update.effective_chat.send_message(
                "Üzr istəyirik, bir xəta baş verdi. Zəhmət olmasa daha sonra yenidən cəhd edin."
            )
    except Exception as e:
        logger.error(f"Error while sending error message: {e}")

# --- Əsas əmrlər ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start əmrini işlədir."""
    user_id = update.message.from_user.id
    database.init_db()
    await update.message.reply_text(
        "Salam! Aşağıdakı menyudan seçim edin:", reply_markup=get_main_menu_keyboard() # Reply Keyboard burada istifadə olunur
    )
    USER_STATES.pop(user_id, None) # Vəziyyəti sıfırla

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline düymə kliklərini idarə edir."""
    query = update.callback_query
    await query.answer() # Kursoru silir
    user_id = query.from_user.id
    USER_STATES.pop(user_id, None) # Hər düymə klikində vəziyyəti sıfırla

    if query.data == "main_menu":
        # Əvvəlki mesajı silib yeni mesaj ReplyKeyboard ilə göndərmək lazımdır
        await query.delete_message()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Salam! Aşağıdakı menyudan seçim edin:",
            reply_markup=get_main_menu_keyboard()
        )
    # digər Inline düymələr bu hissədə qalır
    elif query.data == "paid_receipt":
        await query.edit_message_text("Çekiniz gözlənilir. Zəhmət olmasa çeki şəkil kimi göndərin.")
        USER_STATES[user_id] = AWAITING_RECEIPT

    elif query.data == "services_menu": # Bu hələ də Inline düymə kimi işləyir
        await query.edit_message_text(
            "Xidmətlər kateqoriyasını seçin:", reply_markup=get_services_menu_keyboard()
        )

    elif query.data == "services_tiktok":
        context.user_data['current_service_category'] = 'tiktok'
        await query.edit_message_text(
            """**Tiktok Xidmətləri:**

- 1000 Bəyəni (Like): {:.2f} AZN
- 1000 İzləyici (Follower): {:.2f} AZN
- 1000 Baxış (View): {:.2f} AZN

Sifariş vermək üçün istədiyiniz sayı və xidməti qeyd edin (məs: "3k like" və ya "2.5k follower").""".format(
                database.get_service_price("tiktok_like"),
                database.get_service_price("tiktok_follower"),
                database.get_service_price("tiktok_view")
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Geri", callback_data="services_menu")]])
        )

    elif query.data == "services_instagram":
        context.user_data['current_service_category'] = 'instagram'
        await query.edit_message_text(
            """**Instagram Xidmətləri:**

- 1000 Bəyəni (Like): {:.2f} AZN
- 1000 İzləyici (Follower): {:.2f} AZN
- 1000 Baxış (View): {:.2f} AZN

Sifariş vermək üçün istədiyiniz sayı və xidməti qeyd edin (məs: "500 like" və ya "1k follower").""".format(
                database.get_service_price("instagram_like"),
                database.get_service_price("instagram_follower"),
                database.get_service_price("instagram_view")
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Geri", callback_data="services_menu")]])
        )

    elif query.data == "services_telegram":
        context.user_data['current_service_category'] = 'telegram'
        await query.edit_message_text(
            """**Telegram Xidmətləri:**

- 1000 Kanal Abunəçisi: {:.2f} AZN
- 1000 Post Baxışı: {:.2f} AZN

Sifariş vermək üçün istədiyiniz sayı və xidməti qeyd edin (məs: "1k abuneci" və ya "10k baxış").""".format(
                database.get_service_price("telegram_subscriber"),
                database.get_service_price("telegram_view")
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Geri", callback_data="services_menu")]])
        )
