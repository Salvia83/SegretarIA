#!/usr/bin/env bash
# ==============================================================================
# SegretarIA - Orchestratore Host Proxmox (Dell OptiPlex 192.168.188.77)
# ==============================================================================
# Eseguito automaticamente AD OGNI AVVIO dal servizio systemd
# segretaria-notte.service (sia alle 03:00 da BIOS sia premendo il tasto fisico
# o via Wake-on-LAN): avvia la pipeline AI dentro LXC 100, attende la fine
# della sincronizzazione Syncthing (+5 minuti di sicurezza) e spegne il Dell.
#
# Opzioni:
#   --no-shutdown   Esegue tutta la pipeline ma NON spegne il server
#   --dry-run       Mostra solo cosa verrebbe elaborato dentro LXC 100
#   --grace SECS    Sovrascrive i secondi di attesa extra Syncthing (default: 300)
#
# Per bloccare temporaneamente lo spegnimento durante manutenzione via SSH:
#   touch /run/segretaria-no-shutdown
# ==============================================================================

set -euo pipefail

CTID=100
GRACE_SECONDS=300
DO_SHUTDOWN=1
DRY_RUN=0
LOCK_FILE="/var/lock/segretaria_notte.lock"
LOG_FILE="/var/log/segretaria_notte_host.log"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-shutdown)
            DO_SHUTDOWN=0
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            DO_SHUTDOWN=0
            shift
            ;;
        --grace)
            GRACE_SECONDS="${2:-300}"
            shift 2
            ;;
        *)
            echo "Opzione sconosciuta: $1" >&2
            exit 1
            ;;
    esac
done

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "[!] Pipeline gia' in esecuzione. Esco."
    exit 0
fi

log "=== AVVIO SEGRETARIA AUTOMATICA (HOST PROXMOX -> LXC $CTID) ==="

if ! pct status "$CTID" | grep -q "status: running"; then
    log "[*] Avvio container LXC $CTID..."
    pct start "$CTID"
fi

# Attende che il container LXC sia pronto ad accettare comandi
for _ in $(seq 1 30); do
    if pct exec "$CTID" -- true 2>/dev/null; then
        break
    fi
    sleep 2
done

ARGS=(--grace-seconds "$GRACE_SECONDS")
if [[ "$DRY_RUN" -eq 1 ]]; then
    ARGS+=(--dry-run)
fi

if [[ -f /etc/default/segretaria ]]; then
    # shellcheck disable=SC1091
    source /etc/default/segretaria
fi

if ! pct exec "$CTID" -- env OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}" python3 /root/SegretarIA/scripts/segretaria_pipeline_notturna.py "${ARGS[@]}"; then
    log "[!] Avviso: la pipeline dentro LXC $CTID ha segnalato un errore."
fi

if [[ -f /run/segretaria-no-shutdown ]]; then
    log "[+] Trovato /run/segretaria-no-shutdown: il server resta acceso per manutenzione."
    exit 0
fi

if [[ "$DO_SHUTDOWN" -eq 1 ]]; then
    log "[*] Elaborazione e sync Syncthing ($GRACE_SECONDS s extra) completati. Spegnimento del Dell tra 10 secondi..."
    sleep 10
    /bin/systemctl poweroff
else
    log "[+] Completato (--no-shutdown / --dry-run attivo: il server resta acceso)."
fi
