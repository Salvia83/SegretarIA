#!/bin/bash
# ==============================================================================
# SegretarIA - Installazione Rapida Syncthing su Container LXC (Debian / Ubuntu)
# ==============================================================================
# Esegui questo script dentro la Console del tuo Container LXC su Proxmox VE.
# Cosa fa:
#   1. Installa Syncthing, Python 3 e curl
#   2. Crea la struttura a 2 cartelle (1_Input e 2_Archivio)
#   3. Abilita l'avvio automatico di Syncthing al boot
#   4. Sblocca l'accesso alla Web GUI (porta 8384) dalla rete locale di casa
# ==============================================================================

set -e

echo "1/4 - Aggiornamento pacchetti e installazione Syncthing..."
apt update && apt install -y syncthing curl python3 nano

echo "2/4 - Creazione cartelle ufficiali SegretarIA (1_Input e 2_Archivio)..."
mkdir -p /root/SegretarIA/1_Input /root/SegretarIA/2_Archivio

echo "3/4 - Attivazione servizio automatico Syncthing..."
systemctl enable --now syncthing@root.service
sleep 4

echo "4/4 - Sblocco interfaccia Web sulla rete locale (0.0.0.0:8384)..."
sed -i 's/127.0.0.1:8384/0.0.0.0:8384/g' /root/.local/state/syncthing/config.xml /root/.config/syncthing/config.xml 2>/dev/null || true
systemctl restart syncthing@root.service

IP_ADDR=$(hostname -I | awk '{print $1}')
echo ""
echo "=============================================================================="
echo " FATTO! Syncthing e' attivo e pronto."
echo " Apri il browser su:  http://${IP_ADDR}:8384"
echo " Cartella 1_Input:    /root/SegretarIA/1_Input"
echo " Cartella 2_Archivio: /root/SegretarIA/2_Archivio"
echo "=============================================================================="
