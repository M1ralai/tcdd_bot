from telegram_notifications import send_telegram_message


if __name__ == "__main__":
    ok = send_telegram_message("Test notification")
    if ok:
        print("[telegram] Test notification gonderildi.")
    else:
        print("[telegram] Test notification gonderilemedi. Env/token/chat_id/loglari kontrol edin.")
