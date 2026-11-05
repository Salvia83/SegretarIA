#!/bin/bash
# ==============================================================================
# SegretarIA - Scarico Automatico Registratore USB su Proxmox VE
# ==============================================================================
# Viene richiamato in automatico da udev + systemd (usb-recorder@.service)
# non appena inserisci il registratore vocale in una porta USB del mini-PC.
# ==============================================================================

DEVICE_NAME="$1"
DEV_PATH="/dev/${DEVICE_NAME}"
MOUNT_POINT="/mnt/usb_recorder"

# ==============================================================================
# CONFIGURAZIONE PERSONALE (Modifica questi 3 valori!)
# ==============================================================================
# ID numerico del tuo container LXC dove gira Syncthing (es. 100 o 101):
LXC_ID="101"

# Opzionale: per ricevere la notifica su Telegram, inserisci Token e User ID:
TELEGRAM_BOT_TOKEN="INSERISCI_QUI_IL_TUO_TOKEN"
TELEGRAM_CHAT_ID="INSERISCI_QUI_IL_TUO_USER_ID"
# ==============================================================================

LOG_FILE="/var/log/segretaria_usb.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rilevato inserimento USB: ${DEV_PATH}" >> "$LOG_FILE"
sleep 2

# Ripara in 0.1s l'eventuale name-hash fuori standard scritto dai chip Jieli su exFAT/FAT32
command -v fsck.exfat >/dev/null 2>&1 && fsck.exfat -y "$DEV_PATH" >> "$LOG_FILE" 2>&1
command -v fsck.vfat  >/dev/null 2>&1 && fsck.vfat -a "$DEV_PATH" >> "$LOG_FILE" 2>&1

mkdir -p "$MOUNT_POINT"
mount -o rw "$DEV_PATH" "$MOUNT_POINT" 2>>"$LOG_FILE" || exit 0

# Controllo di sicurezza: se non e' il registratore vocale, smonta subito senza toccare nulla!
if [ ! -f "$MOUNT_POINT/MRECSET.txt" ] && [ ! -d "$MOUNT_POINT/RECORD" ]; then
    echo "Non e' il registratore vocale. Smonto e ignoro." >> "$LOG_FILE"
    umount "$MOUNT_POINT"
    exit 0
fi

TARGET_DIR="/root/SegretarIA/1_Input"

COUNT=0
shopt -s nullglob nocaseglob
for AUDIO_FILE in "$MOUNT_POINT"/RECORD/*.mp3 "$MOUNT_POINT"/RECORD/*.wav "$MOUNT_POINT"/*.mp3 "$MOUNT_POINT"/*.wav; do
    if [ -f "$AUDIO_FILE" ]; then
        BASENAME=$(basename "$AUDIO_FILE")
        pct push "$LXC_ID" "$AUDIO_FILE" "${TARGET_DIR}/${BASENAME}" 2>>"$LOG_FILE"
        if [ $? -eq 0 ]; then
            rm -f "$AUDIO_FILE"
            COUNT=$((COUNT + 1))
            echo " -> Scaricato: ${BASENAME}" >> "$LOG_FILE"
        fi
    fi
done

pct exec "$LXC_ID" -- chown -R root:root "$TARGET_DIR" 2>/dev/null

# Aggiorna l'orologio interno del registratore (MRECSET.txt)
if [ -f "$MOUNT_POINT/MRECSET.txt" ]; then
    NOW_TIME=$(date '+%H:%M %Y/%m/%d')
    sed -i "s|^TIME:.*|TIME:${NOW_TIME}\r|" "$MOUNT_POINT/MRECSET.txt"
    echo "Orologio MRECSET.txt aggiornato a: TIME:${NOW_TIME}" >> "$LOG_FILE"
fi

sync
umount "$MOUNT_POINT"
echo "Chiavetta smontata (alimentazione +5V attiva per ricarica). File scaricati: ${COUNT}" >> "$LOG_FILE"

# Segnale acustico dallo speaker interno del mini-PC (se presente)
amixer -c 0 set 'Auto-Mute Mode' Disabled >/dev/null 2>&1
amixer -c 0 set Master 100% unmute >/dev/null 2>&1
amixer -c 0 set Speaker 100% unmute >/dev/null 2>&1
if [ -f /usr/local/share/segretaria_beep.wav ]; then
    aplay -q -D plughw:0,0 /usr/local/share/segretaria_beep.wav 2>/dev/null
fi

# Notifica Telegram (se configurata)
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "INSERISCI_QUI_IL_TUO_TOKEN" ]; then
    MSG="✅ Registratore USB Sincronizzato!%0A🎙️ File scaricati in 1_Input: ${COUNT}%0A🕒 Orologio aggiornato.%0A🔋 Puoi staccarla subito o lasciarla in carica!"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${MSG}" >> "$LOG_FILE" 2>&1
    echo "" >> "$LOG_FILE"
fi
