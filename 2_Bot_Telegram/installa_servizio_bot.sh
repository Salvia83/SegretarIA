#!/bin/bash
# ==============================================================================
# SegretarIA - Attivazione Servizio Automatico H24 per il Bot Telegram
# ==============================================================================
# Esegui questo script dentro il container LXC dopo aver configurato
# BOT_TOKEN e ALLOWED_USER_ID in /root/SegretarIA/telegram_bot.py
# ==============================================================================

SCRIPT_DEST="/root/SegretarIA/telegram_bot.py"

if [ -f "./telegram_bot_ingestor.py" ] && [ ! -f "$SCRIPT_DEST" ]; then
    mkdir -p /root/SegretarIA
    cp ./telegram_bot_ingestor.py "$SCRIPT_DEST"
fi

chmod +x "$SCRIPT_DEST"

cat << 'EOF' > /etc/systemd/system/segretaria-telegram.service
[Unit]
Description=Bot Telegram SegretarIA
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /root/SegretarIA/telegram_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now segretaria-telegram.service
systemctl status segretaria-telegram.service --no-pager
