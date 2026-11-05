#!/bin/bash
# ==============================================================================
# SegretarIA - Scarico Automatico Registratore USB su macOS
# ==============================================================================

# ==============================================================================
# CONFIGURAZIONE PERSONALE (Modifica con il percorso della tua cartella Syncthing!)
# ==============================================================================
TARGET_DIR="$HOME/SyncThing/SegretarIA - Input"

# Opzionale: inserisci Token e User ID se vuoi ricevere anche l'avviso su Telegram
TELEGRAM_BOT_TOKEN="INSERISCI_QUI_IL_TUO_TOKEN"
TELEGRAM_CHAT_ID="INSERISCI_QUI_IL_TUO_USER_ID"
# ==============================================================================

sleep 2
shopt -s nullglob nocaseglob

for VOL in /Volumes/*; do
    if [ -f "$VOL/MRECSET.txt" ] || [ -d "$VOL/RECORD" ]; then
        mkdir -p "$TARGET_DIR"
        COUNT=0

        for AUDIO_FILE in "$VOL"/RECORD/*.mp3 "$VOL"/RECORD/*.wav "$VOL"/*.mp3 "$VOL"/*.wav; do
            if [ -f "$AUDIO_FILE" ]; then
                BASENAME=$(basename "$AUDIO_FILE")
                cp -f "$AUDIO_FILE" "$TARGET_DIR/$BASENAME"
                if [ $? -eq 0 ]; then
                    rm -f "$AUDIO_FILE"
                    COUNT=$((COUNT + 1))
                fi
            fi
        done

        # Aggiorna l'orologio interno in MRECSET.txt (formato TIME:HH:MM YYYY/MM/DD)
        if [ -f "$VOL/MRECSET.txt" ]; then
            NOW_TIME=$(date '+%H:%M %Y/%m/%d')
            sed -i '' "s|^TIME:.*|TIME:${NOW_TIME}|" "$VOL/MRECSET.txt"
        fi

        sync
        diskutil eject "$VOL" >/dev/null 2>&1

        afplay /System/Library/Sounds/Glass.aiff &
        osascript -e "display notification \"Scaricati ${COUNT} file audio e orologio aggiornato.\" with title \"SegretarIA\" subtitle \"Puoi staccare la chiavetta USB!\""

        if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "INSERISCI_QUI_IL_TUO_TOKEN" ]; then
            MSG="✅ Registratore USB Sincronizzato (da Mac)!%0A🎙️ File scaricati: ${COUNT}%0A🕒 Orologio aggiornato.%0A🔋 Puoi staccarla o lasciarla in carica!"
            curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
                -d "chat_id=${TELEGRAM_CHAT_ID}" \
                -d "text=${MSG}" >/dev/null 2>&1 &
        fi

        say "Registrazioni scaricate, puoi staccare la chiavetta"
    fi
done
