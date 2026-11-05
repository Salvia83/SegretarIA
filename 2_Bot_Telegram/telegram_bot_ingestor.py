#!/usr/bin/env python3
"""
SegretarIA - Bot Telegram "Imbuto Universale" (Zero Dipendenze Esterne)
Funziona direttamente con Python 3 standard (nessun 'pip install' richiesto!).

Cosa riceve e salva automaticamente nella cartella 1_Input:
  - Note vocali -> TG_VOCALE_YYYYMMDD_HHMMSS.ogg
  - File audio  -> TG_AUDIO_YYYYMMDD_HHMMSS.mp3
  - Foto        -> TG_FOTO_YYYYMMDD_HHMMSS.jpg (+ eventuale didascalia .txt)
  - Documenti   -> TG_DOC_YYYYMMDD_HHMMSS_<nomefile>
  - Testi/Link  -> TG_TESTO_YYYYMMDD_HHMMSS.txt
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE PERSONALE (Compila i tuoi dati qui sotto!)
# ==============================================================================
# 1. Incolla qui tra le virgolette il Token che ti ha fornito @BotFather su Telegram:
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "INSERISCI_QUI_IL_TUO_TOKEN")

# 2. Sicurezza: inserisci il tuo User ID numerico Telegram per bloccare chiunque altro.
#    Lascia pure 0 al primo avvio: manda /start al tuo bot e lui ti scriverà il tuo numero!
#    Poi fermalo, scrivi qui il tuo numero al posto di 0 e riavvialo.
ALLOWED_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

# 3. Percorso della cartella 1_Input sincronizzata con Syncthing:
INPUT_DIR = os.environ.get("SEGRETARIA_INPUT_DIR", "/root/SegretarIA/1_Input")
# ==============================================================================

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_BASE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"


def api_call(method: str, params: dict = None) -> dict:
    url = f"{API_BASE}/{method}"
    if params:
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=data)
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_reply(chat_id: int, text: str):
    try:
        api_call("sendMessage", {"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"[Errore invio risposta] {e}")


def download_telegram_file(file_id: str, dest_path: str):
    info = api_call("getFile", {"file_id": file_id})
    file_path = info["result"]["file_path"]
    url = f"{FILE_BASE}/{file_path}"
    urllib.request.urlretrieve(url, dest_path)


def handle_message(msg: dict):
    user = msg.get("from", {})
    user_id = user.get("id", 0)
    username = user.get("first_name", "Utente")
    chat_id = msg["chat"]["id"]

    # Controllo sicurezza User ID
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        print(f"[BLOCCATO] Tentativo da user_id non autorizzato: {user_id}")
        return

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(INPUT_DIR, exist_ok=True)

    # Comando /start o /id
    text = msg.get("text", "").strip()
    if text in ("/start", "/id"):
        avviso_sicurezza = (
            "\n⚠️ Ricordati di inserire questo User ID in ALLOWED_USER_ID dentro lo script!"
            if ALLOWED_USER_ID == 0
            else "\n🔒 Bot protetto: risponde solo al tuo User ID."
        )
        send_reply(
            chat_id,
            f"👋 Ciao {username}! Sono il tuo Bot privato SegretarIA.\n"
            f"🔑 Il tuo User ID personale è: {user_id}{avviso_sicurezza}\n\n"
            f"Mandami pure:\n"
            f"🎙️ Note vocali o file audio\n"
            f"📸 Foto (prodotti, etichette, locandine, appunti)\n"
            f"📎 Documenti PDF\n"
            f"📝 Testi scritti o link web\n"
            f"Li salverò all'istante in 1_Input!",
        )
        return

    # 1. NOTA VOCALE (Voice)
    if "voice" in msg:
        file_id = msg["voice"]["file_id"]
        filename = f"TG_VOCALE_{now_str}.ogg"
        dest = os.path.join(INPUT_DIR, filename)
        download_telegram_file(file_id, dest)
        print(f"[OK] Salvato vocale: {dest}")
        send_reply(chat_id, f"🎙️ Vocale salvato in 1_Input!\n({filename})")
        return

    # 2. FILE AUDIO
    if "audio" in msg:
        file_id = msg["audio"]["file_id"]
        orig_name = msg["audio"].get("file_name", "audio.mp3")
        ext = os.path.splitext(orig_name)[1] or ".mp3"
        filename = f"TG_AUDIO_{now_str}{ext}"
        dest = os.path.join(INPUT_DIR, filename)
        download_telegram_file(file_id, dest)
        print(f"[OK] Salvato audio: {dest}")
        send_reply(chat_id, f"🎵 File audio salvato in 1_Input!\n({filename})")
        return

    # 3. FOTO
    if "photo" in msg:
        best_photo = msg["photo"][-1]
        file_id = best_photo["file_id"]
        filename = f"TG_FOTO_{now_str}.jpg"
        dest = os.path.join(INPUT_DIR, filename)
        download_telegram_file(file_id, dest)
        caption = msg.get("caption", "").strip()
        if caption:
            caption_file = os.path.join(INPUT_DIR, f"TG_FOTO_{now_str}_nota.txt")
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(caption + "\n")
        print(f"[OK] Salvata foto: {dest}")
        send_reply(chat_id, f"📸 Foto salvata in 1_Input!\n({filename})")
        return

    # 4. DOCUMENTO GENERICO
    if "document" in msg:
        file_id = msg["document"]["file_id"]
        orig_name = os.path.basename(msg["document"].get("file_name", f"doc_{now_str}"))
        filename = f"TG_DOC_{now_str}_{orig_name}"
        dest = os.path.join(INPUT_DIR, filename)
        download_telegram_file(file_id, dest)
        print(f"[OK] Salvato documento: {dest}")
        send_reply(chat_id, f"📎 Documento salvato in 1_Input!\n({filename})")
        return

    # 5. TESTO SCRITTO O LINK WEB
    if text:
        filename = f"TG_TESTO_{now_str}.txt"
        dest = os.path.join(INPUT_DIR, filename)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[OK] Salvato testo/link: {dest}")
        send_reply(chat_id, f"📝 Testo/Link salvato in 1_Input!\n({filename})")


def main():
    if BOT_TOKEN == "INSERISCI_QUI_IL_TUO_TOKEN" or not BOT_TOKEN:
        print("❌ ERRORE: Apri telegram_bot_ingestor.py e inserisci il tuo BOT_TOKEN dato da @BotFather!")
        return

    print(f"🚀 Bot SegretarIA avviato! Cartella target: {INPUT_DIR}")
    offset = 0
    while True:
        try:
            res = api_call("getUpdates", {"offset": offset, "timeout": 30})
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    handle_message(upd["message"])
        except KeyboardInterrupt:
            print("\nBot fermato.")
            break
        except Exception as e:
            print(f"[Riconnessione in corso...] {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
