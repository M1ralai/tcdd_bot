import json
import os
import urllib.error
import urllib.request

from env_loader import load_env


TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
DEFAULT_TIMEOUT_SECONDS = 10


def send_telegram_message(message: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> bool:
    """Send a Telegram message if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID yok; bildirim devre dışı.")
        return False

    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        TELEGRAM_API_URL.format(token=token),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            if response.status != 200:
                print(f"[telegram] sendMessage basarisiz: HTTP {response.status} - {response_body}")
                return False

            data = json.loads(response_body) if response_body else {}
            if not data.get("ok"):
                print(f"[telegram] sendMessage hata dondu: {data}")
                return False

            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[telegram] HTTP hata: {e.code} - {error_body}")
    except Exception as e:
        print(f"[telegram] Bildirim gonderilemedi: {e}")

    return False
