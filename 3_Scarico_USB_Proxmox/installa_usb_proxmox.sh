#!/bin/bash
# ==============================================================================
# SegretarIA - Installer Automatico Regola USB su Nodo Host Proxmox VE
# ==============================================================================
# Esegui questo script sulla Shell del nodo principale Proxmox (NON nel container!)
# dopo aver inserito LXC_ID (ed eventuale Telegram) in usb_recorder_ingest.sh.
# ==============================================================================

set -e

echo "1/4 - Installazione supporto exFAT e utilita' audio..."
apt update && apt install -y exfatprogs dosfstools alsa-utils python3 curl

echo "2/4 - Generazione suono stereo di conferma (/usr/local/share/segretaria_beep.wav)..."
python3 - << 'PYEOF'
import math, struct, wave
rate = 44100
samples = []
for freq, dur in [(880, 0.14), (0, 0.06), (1320, 0.22)]:
    for i in range(int(rate * dur)):
        val = int(22000 * math.sin(2 * math.pi * freq * i / rate)) if freq > 0 else 0
        samples.append(struct.pack('<hh', val, val))
with wave.open('/usr/local/share/segretaria_beep.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b''.join(samples))
PYEOF

amixer -c 0 sset 'Auto-Mute Mode' Disabled >/dev/null 2>&1 || true
amixer -c 0 sset 'Master' 100% unmute >/dev/null 2>&1 || true
amixer -c 0 sset 'Speaker' 100% unmute >/dev/null 2>&1 || true
alsactl store >/dev/null 2>&1 || true

echo "3/4 - Copia script /usr/local/bin/usb_recorder_ingest.sh..."
cp ./usb_recorder_ingest.sh /usr/local/bin/usb_recorder_ingest.sh
chmod +x /usr/local/bin/usb_recorder_ingest.sh

echo "4/4 - Attivazione servizio systemd e regola udev..."
cat << 'EOF' > /etc/systemd/system/usb-recorder@.service
[Unit]
Description=Scarico Automatico Registratore Vocale USB su %i

[Service]
Type=oneshot
ExecStart=/usr/local/bin/usb_recorder_ingest.sh %i
EOF

cat << 'EOF' > /etc/udev/rules.d/99-usb-recorder.rules
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="exfat|vfat", TAG+="systemd", ENV{SYSTEMD_WANTS}="usb-recorder@%k.service"
EOF

systemctl daemon-reload
udevadm control --reload-rules && udevadm trigger

echo ""
echo "✅ Installazione completata! Ora prova a inserire il registratore USB."
