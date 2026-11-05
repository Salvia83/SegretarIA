#!/bin/bash
# ==============================================================================
# SegretarIA - Installer Automatico Guardiano USB per macOS
# ==============================================================================
# Crea la micro-app nativa SegretarIA_USB.app (necessaria per far apparire il
# permesso ufficiale macOS "Consenti accesso ai volumi rimovibili") e registra
# il LaunchAgent che si sveglia solo quando viene collegata una chiavetta USB.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SH_PATH="${SCRIPT_DIR}/mac_usb_recorder_ingest.sh"
APP_PATH="${SCRIPT_DIR}/SegretarIA_USB.app"
PLIST_PATH="$HOME/Library/LaunchAgents/com.segretaria.usbingest.plist"

chmod +x "$SH_PATH"

echo "1/2 - Compilazione micro-app nativa SegretarIA_USB.app..."
rm -rf "$APP_PATH"
osacompile -o "$APP_PATH" -e "do shell script \"\\\"${SH_PATH}\\\"\""

echo "2/2 - Registrazione LaunchAgent su /Volumes..."
mkdir -p "$HOME/Library/LaunchAgents"
cat << EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.segretaria.usbingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-g</string>
        <string>${APP_PATH}</string>
    </array>
    <key>WatchPaths</key>
    <array>
        <string>/Volumes</string>
    </array>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "✅ Fatto! Al primo inserimento del registratore USB clicca 'Consenti' sul popup di macOS."
