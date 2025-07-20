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
    elif query.data.startswith("admin_reply_to_user_"):
        # Adminin istifadəçiyə cavab düyməsi kliklənəndə
        target_user_id = int(query.data.split("_")[-1])
        context.user_data['reply_target_user_id'] = target_user_id
        await query.edit_message_text(
            f"İstifadəçi `{target_user_id}` üçün cavabınızı yazın."
        )
        USER_STATES[user_id] = AWAITING_ADMIN_REPLY

# --- Mesaj idarəçiliyi ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text.lower()

    # ReplyKeyboardMarkup düymələrindən gələn mətnləri yoxlayırıq
    if text == "balans artır":
        await update.message.reply_text(
            """Balansınızı artırmaq üçün aşağıdakı hesablardan birinə ödəniş edə bilərsiniz:

**Kapital Bank**: XXXX XXXX XXXX XXXX (Adınız, Soyadınız)
**Leobank**: XXXX XXXX XXXX XXXX (Adınız, Soyadınız)

Ödəniş etdikdən sonra çeki (skrinşotu) göndərin və "Ödənildi" düyməsinə klikləyin.
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ödənildi", callback_data="paid_receipt")]])
        )
        USER_STATES[user_id] = AWAITING_RECEIPT
    elif text == "balansa baxmaq":
        balance = database.get_user_balance(user_id)
        await update.message.reply_text(f"Sizin cari balansınız: **{balance:.2f} AZN**.", parse_mode="Markdown")
    elif text == "xidmətlər":
        await update.message.reply_text(
            "Xidmətlər kateqoriyasını seçin:", reply_markup=get_services_menu_keyboard()
        )
    elif text == "adminlə əlaqə":
        await update.message.reply_text(
            "Adminlə əlaqə saxlamaq üçün mesajınızı birbaşa yaza bilərsiniz. Mesajınız adminə yönləndiriləcək."
        )
        USER_STATES[user_id] = AWAITING_ADMIN_REPLY

    # Admin qiymət dəyişdirir
    elif user_id == config.ADMIN_ID and USER_STATES.get(user_id) == AWAITING_ADMIN_PRICE_CHANGE_AMOUNT:
        try:
            new_price = float(text)
            if new_price <= 0:
                await update.message.reply_text("Qiymət müsbət ədəd olmalıdır.")
                USER_STATES.pop(user_id, None)
                return

            service_to_change = context.user_data.get('service_to_change_price')
            if service_to_change:
                database.update_service_price(service_to_change, new_price)
                await update.message.reply_text(f"`{service_to_change}` xidmətinin qiyməti `{new_price:.2f} AZN` olaraq yeniləndi.", parse_mode="Markdown")
            else:
                await update.message.reply_text("Xəta: Qiyməti dəyişdiriləcək xidmət tapılmadı.")
            USER_STATES.pop(user_id, None)
            context.user_data.pop('service_to_change_price', None)
        except ValueError:
            await update.message.reply_text("Yanlış qiymət formatı. Rəqəm daxil edin.")
            USER_STATES.pop(user_id, None)

    # Admin istifadəçiyə cavab yazır
    elif user_id == config.ADMIN_ID and 'reply_target_user_id' in context.user_data and USER_STATES.get(user_id) == AWAITING_ADMIN_REPLY:
        target_user_id = context.user_data.pop('reply_target_user_id')
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"**Admindən cavab:**\n\n{update.message.text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"Mesajınız istifadəçi `{target_user_id}`a göndərildi.")
        except Exception as e:
            logger.error(f"Failed to send admin reply to user {target_user_id}: {e}")
            await update.message.reply_text(f"Mesajı istifadəçiyə göndərərkən xəta: {e}")
        USER_STATES.pop(user_id, None)

    # Sifariş linki gözlənilir
    elif USER_STATES.get(user_id) == AWAITING_LINK:
        service_data = context.user_data.get('current_order')
        if not service_data:
            await update.message.reply_text("Xəta: Sifariş məlumatı tapılmadı. Zəhmət olmasa yenidən sifariş edin.", reply_markup=get_main_menu_keyboard())
            USER_STATES.pop(user_id, None)
            return

        link = update.message.text
        if not is_valid_url(link):
            await update.message.reply_text("Yanlış link formatı. Zəhmət olmasa düzgün Telegram, Instagram, və ya Tiktok linki göndərin.")
            return

        service_type = service_data['service_type']
        amount = service_data['amount']
        
        # Balansdan çıxarış
        current_balance = database.get_user_balance(user_id)
        if current_balance < service_data['total_cost']:
            await update.message.reply_text(f"Xəta: Balansınız sifariş üçün kifayət deyil. Cari balansınız: **{current_balance:.2f} AZN**. Zəhmət olmasa balansınızı artırın.", parse_mode="Markdown")
            USER_STATES.pop(user_id, None)
            context.user_data.pop('current_order', None)
            return

        database.update_user_balance(user_id, -service_data['total_cost']) # Balansdan çıxarılır

        order_id = database.add_order(user_id, service_type, amount, link)

        await update.message.reply_text(f"Sifarişiniz (`{order_id}`) qeydə alındı! Tezliklə tamamlanacaq. Yeni balansınız: **{database.get_user_balance(user_id):.2f} AZN**.", parse_mode="Markdown")
        
        # Adminə sifariş bildirişi
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"**Yeni Sifariş!**\n"
                 f"İstifadəçi ID: `{user_id}`\n"
                 f"Xidmət: `{service_type}`\n"
                 f"Miqdar: `{amount}`\n"
                 f"Link: `{link}`\n"
                 f"Sifariş ID: `{order_id}`\n\n"
                 f"Sifarişi tamamladıqda `/done {order_id}` yazın.",
            parse_mode="Markdown"
        )
        USER_STATES.pop(user_id, None)
        context.user_data.pop('current_order', None)

    # İstifadəçidən adminə mesaj yönləndirmə
    elif USER_STATES.get(user_id) == AWAITING_ADMIN_REPLY:
        admin_msg = await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"**İstifadəçidən mesaj (`{user_id}`):**\n\n{update.message.text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cavab ver", callback_data=f"admin_reply_to_user_{user_id}")]])
        )
        database.save_admin_message_mapping(user_id, admin_msg.message_id)
        
        await update.message.reply_text("Mesajınız adminə çatdırıldı. Tezliklə cavab gözləyin.")
        USER_STATES.pop(user_id, None)

    # Xidmət sifarişlərini emal et (bu hissə hələ də ReplyKeyboard ilə yox, manual mətn daxil etməklə işləyir)
    else:
        match = re.match(r"(\d+\.?\d*)\s*(k)?\s*(like|follower|view|abuneci|baxis)", text)
        if match:
            num_str, k_prefix, service_keyword = match.groups()
            try:
                amount_base = float(num_str) * (1000 if k_prefix else 1)
            except ValueError:
                await update.message.reply_text("Yanlış miqdar formatı. Məsələn, '3k' və ya '500' yazın.")
                return

            service_type_full = None
            current_category = context.user_data.get('current_service_category', '')

            if "like" in service_keyword:
                service_type_full = "tiktok_like" if "tiktok" in current_category else "instagram_like"
            elif "follower" in service_keyword:
                service_type_full = "tiktok_follower" if "tiktok" in current_category else "instagram_follower"
            elif "view" in service_keyword:
                service_type_full = "tiktok_view" if "tiktok" in current_category else ("instagram_view" if "instagram" in current_category else "telegram_view")
            elif "abuneci" in service_keyword:
                service_type_full = "telegram_subscriber"
            elif "baxis" in service_keyword:
                service_type_full = "telegram_view"
            
            if service_type_full:
                price_per_k = database.get_service_price(service_type_full)
                if price_per_k is None:
                    await update.message.reply_text("Bu xidmət növü tapılmadı. Zəhmət olmasa düzgün xidmət növü seçin.")
                    return

                total_cost = (amount_base / 1000) * price_per_k
                user_balance = database.get_user_balance(user_id)

                if user_balance >= total_cost:
                    context.user_data['current_order'] = {
                        'service_type': service_type_full,
                        'amount': amount_base,
                        'total_cost': total_cost
                    }
                    await update.message.reply_text("Post/səhifə linkini göndərin.")
                    USER_STATES[user_id] = AWAITING_LINK
                else:
                    needed_amount = total_cost - user_balance
                    await update.message.reply_text(
                        f"Balansınız kifayət deyil. Bu sifariş ({amount_base} {service_keyword}) üçün sizə **{needed_amount:.2f} AZN** lazımdır. Balansınızı artırmaq üçün 'Balans artır' düyməsinə klikləyin.",
                        parse_mode="Markdown",
                        # Əgər balans artır düyməsi daimi klaviaturadadırsa, burada ReplyKeyboard göstərmək olar
                        # Lakin bu məqsədlə istifadəçini əsas menyuya yönləndirmək daha məntiqlidir.
                    )
            else:
                await update.message.reply_text("Anlaşılmayan sifariş formatı. Zəhmət olmasa '3k like' kimi yazın.")
        else:
            # Əgər heç bir əmr və ya sifariş formatı deyilsə, əsas menyunu göstər.
            await update.message.reply_text(
                "Mən sizi başa düşmədim. Zəhmət olmasa menyudan seçim edin:", reply_markup=get_main_menu_keyboard()
            )


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if USER_STATES.get(user_id) == AWAITING_RECEIPT:
        photo_file = update.message.photo[-1].file_id # Ən böyük şəkli götür
        admin_message = await context.bot.send_photo(
            chat_id=config.ADMIN_ID,
            photo=photo_file,
            caption=f"**Yeni ödəniş çeki!**\nİstifadəçi ID: `{user_id}`\n\n"
                    f"Balansı artırmaq üçün `/add {user_id} <məbləğ>` yazın.",
            parse_mode="Markdown"
        )
        await update.message.reply_text("Çekiniz uğurla göndərildi. Balansınızın təsdiqlənməsini gözləyin.")
        USER_STATES.pop(user_id, None)
    else:
        await update.message.reply_text("Mən bu şəkli nə üçün istifadə edəcəyimi bilmirəm. Zəhmət olmasa menyudan seçim edin.")

# --- Admin əmrləri ---
async def add_balance_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin üçün balans artırma əmri: /add <istifadeçi_id> <mebleğ>"""
    if update.message.from_user.id != config.ADMIN_ID:
        await update.message.reply_text("Sizin bu əmri istifadə etmək səlahiyyətiniz yoxdur.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Yanlış format. İstifadə: `/add <istifadəçi_id> <məbləğ>`")
        return

    try:
        target_user_id = int(args[0])
        amount = float(args[1])
        if amount <= 0:
            await update.message.reply_text("Məbləğ müsbət ədəd olmalıdır.")
            return

        old_balance = database.get_user_balance(target_user_id)
        database.update_user_balance(target_user_id, amount)
        new_balance = database.get_user_balance(target_user_id)

        await update.message.reply_text(
            f"İstifadəçi `{target_user_id}` balansına `{amount:.2f} AZN` əlavə olundu. Yeni balans: `{new_balance:.2f} AZN`.",
            parse_mode="Markdown"
        )
        # İstifadəçiyə bildiriş göndər
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Hörmətli istifadəçi, `{amount:.2f} AZN` balansınıza əlavə olundu. Yeni balansınız: **{new_balance:.2f} AZN**.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not send message to user {target_user_id}: {e}")
            await update.message.reply_text(f"İstifadəçiyə bildiriş göndərilərkən xəta: {e}")

    except ValueError:
        await update.message.reply_text("İstifadəçi ID və ya məbləğ düzgün formatda deyil.")

async def done_order_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin üçün sifarişi tamamlama əmri: /done <sifariş_id>"""
    if update.message.from_user.id != config.ADMIN_ID:
        await update.message.reply_text("Sizin bu əmri istifadə etmək səlahiyyətiniz yoxdur.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Yanlış format. İstifadə: `/done <sifariş_id>`")
        return

    try:
        order_id = int(args[0])
        order_details = database.get_order_details(order_id)

        if not order_details:
            await update.message.reply_text(f"Sifariş ID `{order_id}` tapılmadı.")
            return

        if order_details[4] == 'completed': # Status indexi 4-dür
            await update.message.reply_text(f"Sifariş `{order_id}` artıq tamamlanmış olaraq qeyd olunub.")
            return

        database.update_order_status(order_id, 'completed')
        
        user_id = order_details[0] # user_id indexi 0-dır
        
        await update.message.reply_text(f"Sifariş `{order_id}` tamamlandı olaraq işarələndi.")
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Hörmətli istifadəçi, sifarişiniz (`{order_id}`) tamamlandı! Xidmətlərimizdən istifadə etdiyiniz üçün təşəkkür edirik.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not send completion message to user {user_id} for order {order_id}: {e}")
            await update.message.reply_text(f"Sifariş `{order_id}` tamamlanma bildirişini istifadəçiyə göndərərkən xəta: {e}")

    except ValueError:
        await update.message.reply_text("Sifariş ID düzgün formatda deyil.")

async def get_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin üçün sifarişlərin siyahısına baxmaq: /orders"""
    if update.message.from_user.id != config.ADMIN_ID:
        await update.message.reply_text("Sizin bu əmri istifadə etmək səlahiyyətiniz yoxdur.")
        return

    orders = database.get_all_orders()
    if not orders:
        await update.message.reply_text("Heç bir sifariş tapılmadı.")
        return

    response_text = "**Bütün Sifarişlər:**\n\n"
    for order in orders:
        order_id, user_id, service_type, amount, link, status, timestamp = order
        response_text += (
            f"ID: `{order_id}` | User: `{user_id}` | Xidmət: `{service_type}` | Miqdar: `{amount}`\n"
            f"Link: {link}\n"
            f"Status: `{status}` | Tarix: `{timestamp}`\n"
            f"-----------------------------------\n"
        )
    
    # Mesaj çox uzun olarsa, hissələrə bölmək lazım ola bilər
    if len(response_text) > 4096:
        for i in range(0, len(response_text), 4096):
            await update.message.reply_text(response_text[i:i+4096], parse_mode="Markdown")
    else:
        await update.message.reply_text(response_text, parse_mode="Markdown")

async def get_balance_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin üçün istifadəçi balansına baxmaq: /get_balance <user_id>"""
    if update.message.from_user.id != config.ADMIN_ID:
        await update.message.reply_text("Sizin bu əmri istifadə etmək səlahiyyətiniz yoxdur.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Yanlış format. İstifadə: `/get_balance <istifadəçi_id>`")
        return

    try:
        target_user_id = int(args[0])
        balance = database.get_user_balance(target_user_id)
        await update.message.reply_text(
            f"İstifadəçi `{target_user_id}` balans: **{balance:.2f} AZN**.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("İstifadəçi ID düzgün formatda deyil.")

async def set_price_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin üçün xidmət qiymətini dəyişmək: /set_price"""
    if update.message.from_user.id != config.ADMIN_ID:
        await update.message.reply_text("Sizin bu əmri istifadə etmək səlahiyyətiniz yoxdur.")
        return

    services = database.get_all_services()
    if not services:
        await update.message.reply_text("Sistemdə heç bir xidmət yoxdur.")
        return

    keyboard = []
    for service_name, price in services:
        keyboard.append([InlineKeyboardButton(f"{service_name.replace('_', ' ').title()}: {price:.2f} AZN", callback_data=f"set_price_{service_name}")])
    keyboard.append([InlineKeyboardButton("Ləğv et", callback_data="main_menu")])

    await update.message.reply_text(
        "Qiymətini dəyişmək istədiyiniz xidməti seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    USER_STATES[update.message.from_user.id] = AWAITING_ADMIN_PRICE_CHANGE_SERVICE

async def handle_admin_set_price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not query.data.startswith("set_price_"):
        return

    service_name = query.data.replace("set_price_", "")
    context.user_data['service_to_change_price'] = service_name
    await query.edit_message_text(f"`{service_name.replace('_', ' ').title()}` üçün yeni qiyməti daxil edin (məs: 1.75).", parse_mode="Markdown")
    USER_STATES[user_id] = AWAITING_ADMIN_PRICE_CHANGE_AMOUNT


def main() -> None:
    """Botu başladır."""
    database.init_db()

    # Render üçün Webhook konfiqurasiyası
    PORT = int(os.environ.get('PORT', '8000'))
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Əmrlər
    application.add_handler(CommandHandler("start", start))

    # Admin əmrləri
    application.add_handler(CommandHandler("add", add_balance_admin))
    application.add_handler(CommandHandler("done", done_order_admin))
    application.add_handler(CommandHandler("orders", get_orders_admin))
    application.add_handler(CommandHandler("get_balance", get_balance_admin))
    application.add_handler(CommandHandler("set_price", set_price_admin))


    # Callback Query idarəçisi (Inline düymə klikləri üçün)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(CallbackQueryHandler(handle_admin_set_price_callback, pattern=r"^set_price_"))


    # Mətn mesajları idarəçisi (ReplyKeyboardMarkup düymələri və sifarişlər üçün)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Şəkil mesajları idarəçisi (çek göndərmək üçün)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Xəta idarəçisi
    application.add_error_handler(error_handler)

    # Botu davamlı dinlə
    if WEBHOOK_URL:
        logger.info(f"Setting up webhook for URL: {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=WEBHOOK_URL + config.BOT_TOKEN
        )
    else:
        logger.info("WEBHOOK_URL not set, running in polling mode (for local development or debugging).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
