#!/bin/bash
# ============================================================
# avvia.sh — Launcher di CyberTaskManager (Linux)
# ============================================================
# Cosa fa:
#  1. Rileva l'ambiente virtuale "venv" nella cartella del progetto.
#  2. Avvia main.py in background, staccato dal terminale (nohup + &),
#     così puoi chiudere il terminale senza chiudere l'app.
#
# Uso manuale: doppio click (se il file manager esegue gli .sh) oppure
#   ./avvia.sh
# da terminale. Per l'avvio automatico all'accesso, vedi README.md.
# ============================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
MAIN_SCRIPT="$PROJECT_DIR/main.py"

if [ -x "$VENV_PYTHON" ]; then
    nohup "$VENV_PYTHON" "$MAIN_SCRIPT" >/dev/null 2>&1 &
    disown
    exit 0
fi

if command -v python3 >/dev/null 2>&1; then
    nohup python3 "$MAIN_SCRIPT" >/dev/null 2>&1 &
    disown
    exit 0
fi

echo "ERRORE: nessun interprete Python trovato (né nel venv né nel PATH)." \
    > "$PROJECT_DIR/avvia_errore.log"
echo "Esegui 'python3 -m venv venv' nella cartella del progetto." \
    >> "$PROJECT_DIR/avvia_errore.log"
exit 1
