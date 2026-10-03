# ⟦ CyberTaskManager ⟧ — v6 (Linux/Arch)

Task Manager cyberpunk a tutto schermo, residente in system tray,
attivabile con la scorciatoia **Win + Ctrl + T**. Versione adattata da
zero per Linux/Arch a partire dalla build Windows originale: stessa
interfaccia e stesse funzionalità, ma con i meccanismi di sistema
(scorciatoia globale, avvio automatico, Wi-Fi, sensori) sostituiti con i
loro equivalenti nativi Linux.

Stack tecnico: **Python 3.11+ / PySide6 (Qt6) / PyOpenGL / psutil /
nvidia-ml-py / soundcard / numpy**.

---

## 0. Differenze principali rispetto alla versione Windows

| Funzione | Windows | Linux (questa build) |
|---|---|---|
| Scorciatoia globale | Registrata automaticamente dall'app | Da collegare TU nelle Impostazioni del desktop (sezione 4) |
| Avvio automatico | Registro di Windows | File `.desktop` in `~/.config/autostart/` |
| Wi-Fi | `netsh` | `nmcli` (NetworkManager), fallback `iw` |
| Temperature/ventole | Richiede LibreHardwareMonitor + admin | `lm-sensors`, funziona SENZA permessi elevati |
| GPU non-NVIDIA | Nome via WMI | Nome via `lspci` |
| Launcher senza terminale | `avvia.bat` | `avvia.sh` |

---

## 1. Prerequisiti (pacchetti di sistema Arch Linux)

Apri un terminale ed esegui:

```bash
sudo pacman -Syu
sudo pacman -S python python-pip base-devel mesa glu qt6-base \
    xcb-util-cursor lm_sensors networkmanager iw
```

Cosa serve ciascuno:
- `python`: su Arch include già il modulo `venv` nella libreria standard
  (non serve un pacchetto separato come su altre distro).
- `base-devel`: strumenti di compilazione, per le poche dipendenze Python
  che ne hanno bisogno (equivalente di "build-essential").
- `mesa`, `glu`: librerie OpenGL/GLU di sistema, necessarie per il
  modello 3D.
- `qt6-base`: porta con sé tutte le librerie xcb/Qt6 di cui l'interfaccia
  grafica ha bisogno (utile soprattutto su installazioni Arch minimali o
  con window manager "da smanettone", dove potrebbero mancare).
- `xcb-util-cursor`: richiesta dal plugin XCB di Qt6.
- `lm_sensors`: per leggere temperature CPU/GPU (vedi sezione 5).
- `networkmanager`: per lo stato del Wi-Fi tramite `nmcli` (se usi un
  altro gestore di rete come `iwd` o `netctl`, va bene lo stesso: l'app
  usa automaticamente `iw` come alternativa, vedi sotto).
- `iw`: strumento generico di query Wi-Fi, usato come fallback quando
  NetworkManager non è il gestore di rete attivo.

---

## 2. Installazione

```bash
# Estrai lo zip in una cartella, poi entra dentro, ad esempio:
cd ~/CyberTaskManager

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Testa che funzioni:

```bash
python3 main.py
```

Se l'icona compare nella system tray senza errori in console, tutto ok.
Chiudi con "Esci definitivamente" dal menu della tray prima di procedere.

> **Nota GNOME**: GNOME "vanilla" nasconde
> le icone della system tray a meno di installare l'estensione
> **"AppIndicator and KStatusNotifierItem Support"** da
> [extensions.gnome.org](https://extensions.gnome.org/extension/615/appindicator-support/).
> Senza, l'app funziona comunque (finestra, hotkey, tutto) ma non vedrai
> l'icona in basso a destra. Su KDE/XFCE/Cinnamon non serve nulla.

---

## 3. Avvio senza terminale

```bash
chmod +x avvia.sh   # una tantum, se il permesso di esecuzione non è già impostato
./avvia.sh
```

Per lanciarlo con doppio click dal file manager o dal menu applicazioni,
crea un lancio da menu (opzionale ma comodo):

```bash
# Sostituisci il percorso con quello reale della tua cartella
sed "s#/PERCORSO/COMPLETO/CyberTaskManager#$(pwd)#" cybertaskmanager.desktop.template \
    > ~/.local/share/applications/cybertaskmanager.desktop
```

Da questo momento "CyberTaskManager" compare anche nel menu applicazioni
del tuo desktop, lanciabile senza terminale.

---

## 4. Scorciatoia globale Win + Ctrl + T (passaggio IMPORTANTE)

A differenza di Windows, qui la combinazione va collegata manualmente
nelle Impostazioni di sistema, puntandola a questo comando:

```
/PERCORSO/COMPLETO/CyberTaskManager/venv/bin/python3 /PERCORSO/COMPLETO/CyberTaskManager/main.py --toggle
```

(sostituisci `/PERCORSO/COMPLETO/` con il percorso reale, es. `/home/micky/CyberTaskManager`)

Questo comando non apre una nuova finestra: dice a quella già in
esecuzione in tray di mostrarsi/nascondersi. **L'app deve già essere
avviata** (con `avvia.sh` o dal menu) perché la scorciatoia funzioni —
esattamente come su Windows.

### Su GNOME
1. Impostazioni → Tastiera → Scorciatoie da tastiera personalizzate →
   "+" (o "Vedi altro" → "Scorciatoie personalizzate").
2. Nome: `CyberTaskManager Toggle`.
3. Comando: incolla la riga sopra (con i tuoi percorsi).
4. Imposta la scorciatoia: premi la combinazione dei tasti Win, Ctrl e T
   insieme quando richiesto.

### Su KDE Plasma
Impostazioni di sistema → Scorciatoie → Scorciatoie personalizzate →
Modifica → Nuovo → Comando/URL globale, incolla il comando e assegna la
combinazione.

### Su XFCE
Impostazioni → Tastiera → Scorciatoie applicazioni → Aggiungi, incolla
il comando e premi la combinazione.

---

## 5. Sensori hardware: temperature e ventole

Su Linux funziona meglio che su Windows, e SENZA permessi da
amministratore:

```bash
sudo apt install lm-sensors
sudo sensors-detect   # rispondi "sì" (o Invio, il default) a tutte le domande
sensors                # verifica che stampi temperature reali
```

Una volta configurato `lm-sensors`, l'app legge automaticamente le
temperature tramite `psutil` — nessuna configurazione aggiuntiva
nell'app stessa. Le ventole sono lette allo stesso modo se la scheda
madre le espone (non tutti i modelli/driver le espongono su Linux).

---

## 6. Audio: microfono e audio di sistema

La libreria `soundcard` funziona su Linux tramite **PulseAudio** o
**PipeWire** (con il layer di compatibilità PulseAudio, installato di
default se usi PipeWire o PulseAudio con GNOME). Se il pannello "SISTEMA
(OUTPUT)" resta piatto, verifica che il servizio audio sia attivo:

```bash
pactl info   # deve rispondere con informazioni sul server, non un errore
```

---

## 7. Wi-Fi

Funziona automaticamente se il sistema usa **NetworkManager** (default
con NetworkManager) tramite il comando `nmcli`. Su installazioni
minimali senza NetworkManager, l'app prova automaticamente `iw` come
fallback. Se sei collegato via cavo Ethernet, il pannello mostra
correttamente "Non connesso" (è il comportamento atteso, riguarda solo
il Wi-Fi).

---

## 8. Avvio automatico all'accesso

Apri le Impostazioni dell'app (menu tray → Impostazioni…) e spunta
"Avvia automaticamente all'accesso": scrive un file `.desktop` in
`~/.config/autostart/`, lo standard XDG rispettato da tutti i desktop
Linux principali. Nessun permesso amministrativo richiesto.

---

## 9. Wayland vs X11

Alcune funzioni di finestra (sempre in primo piano, posizionamento a
tutto schermo forzato) sono più affidabili su **X11** che su **Wayland**,
per via delle restrizioni di sicurezza che Wayland impone ai
compositor. Se noti stranezze con la finestra a tutto schermo o con la
finestra che non sta sempre in primo piano, prova ad accedere scegliendo
"GNOME su Xorg" (o l'equivalente del tuo display manager) dalla schermata di login (icona a forma di
ingranaggio vicino al pulsante di accesso).

---

## 10. Compilare in un eseguibile standalone

```bash
pip install pyinstaller
pyinstaller build_exe.spec
```

Eseguibile in `dist/CyberTaskManager/CyberTaskManager` (ELF Linux,
nessuna console). Aggiorna `avvia.sh` o il file `.desktop` per puntare
lì invece che a `main.py` se preferisci distribuire solo l'eseguibile
compilato.

---

## 11. Note di sicurezza e privacy

- Nessun dato lascia il PC: hardware, audio e Wi-Fi restano locali.
- Il meccanismo hotkey usa solo un pidfile locale e un segnale Unix
  standard (SIGUSR1): nessun hook di tastiera globale, nessun permesso
  speciale richiesto.
- I livelli audio sono numeri (0-100%), mai registrazioni salvate.

---

## 12. Troubleshooting rapido

| Problema | Causa probabile | Soluzione |
|---|---|---|
| Non vedo l'icona in system tray | GNOME senza estensione AppIndicator | Sezione 2 — l'app funziona comunque, manca solo l'icona |
| Win+Ctrl+T non fa nulla | Scorciatoia non configurata, o app non avviata | Sezione 4 — l'app deve già essere in esecuzione |
| `ModuleNotFoundError` all'avvio | Dipendenze non installate nel venv attivo | `source venv/bin/activate` poi `pip install -r requirements.txt` |
| Temperature sempre "spente" | `lm-sensors` non configurato | Sezione 5 |
| Audio di sistema piatto | PulseAudio/PipeWire non attivo | Sezione 6 |
| Wi-Fi "Non connesso" ma sei online | Sei su Ethernet, oppure NetworkManager non gestisce l'interfaccia | Comportamento atteso nel primo caso; nel secondo verifica `nmcli dev status` |
| Finestra a tutto schermo si comporta in modo strano | Sessione Wayland | Prova con "GNOME su Xorg" (sezione 9) |
| Vuoi chiudere l'app del tutto | ESC/chiusura finestra nasconde soltanto | "Esci definitivamente" dal menu della system tray |
