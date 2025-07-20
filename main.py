def main() -> None:
    """Botu başladır."""
    database.init_db() # Veritabanını başlat

    # Render üçün Webhook konfiqurasiyası
    # TelegramWebhookBot (Long Polling yerine Webhook)
    PORT = int(os.environ.get('PORT', '8000')) # Render avtomatik olaraq PORT dəyişəni təyin edir
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL') # Render-də ətraf mühit dəyişəni kimi qurulacaq

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Əmrlər
    application.add_handler(CommandHandler("start", start))

    # Admin əmrləri
    application.add_handler(CommandHandler("add", add_balance_admin))
    application.add_handler(CommandHandler("done", done_order_admin))
    application.add_handler(CommandHandler("orders", get_orders_admin))
    application.add_handler(CommandHandler("get_balance", get_balance_admin))
    application.add_handler(CommandHandler("set_price", set_price_admin))

    # Callback Query idarəçisi (düymə klikləri üçün)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(CallbackQueryHandler(handle_admin_set_price_callback, pattern=r"^set_price_"))

    # Mətn mesajları idarəçisi (sifarişlər və adminlə əlaqə üçün)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Şəkil mesajları idarəçisi (çek göndərmək üçün)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Xəta idarəçisi
    application.add_error_handler(error_handler)

    # Render üzərində Webhook istifadə et
    if WEBHOOK_URL:
        logger.info(f"Setting up webhook for URL: {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=config.BOT_TOKEN, # Telegram Webhook üçün path token olaraq təyin olunur
            webhook_url=WEBHOOK_URL + config.BOT_TOKEN
        )
    else:
        logger.info("WEBHOOK_URL not set, running in polling mode (for local development or debugging).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

# Main bot code placeholder
