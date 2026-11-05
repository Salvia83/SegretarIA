# ==============================================================================
# SegretarIA - Scarico Automatico Registratore USB su Windows
# ==============================================================================

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ==============================================================================
# CONFIGURAZIONE PERSONALE (Modifica questi percorsi/valori!)
# ==============================================================================
# 1. Cartella 1_Input di Syncthing sul tuo PC Windows:
$TargetDir = "$env:USERPROFILE\Syncthing\SegretarIA - Input"

# 2. Opzionale: inserisci Token e User ID se vuoi ricevere la notifica Telegram
$BotToken  = "INSERISCI_QUI_IL_TUO_TOKEN"
$ChatId    = "INSERISCI_QUI_IL_TUO_USER_ID"
# ==============================================================================

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

Add-Type -AssemblyName System.Speech
$Voice = New-Object System.Speech.Synthesis.SpeechSynthesizer

function Process-RecorderDrive {
    $RemovableDrives = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DriveType -eq 2 }
    foreach ($Drive in $RemovableDrives) {
        $DriveRoot  = "$($Drive.DeviceID)\"
        $ConfigFile = "${DriveRoot}MRECSET.txt"
        $RecordDir  = "${DriveRoot}RECORD"

        if ((Test-Path $ConfigFile) -or (Test-Path $RecordDir)) {
            Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Registratore rilevato su $($Drive.DeviceID)!" -ForegroundColor Green
            Start-Sleep -Seconds 1
            $Count = 0

            # Sposta i file .mp3 e .wav dentro la cartella 1_Input di Syncthing
            if (Test-Path $RecordDir) {
                $Files = Get-ChildItem -Path "$RecordDir\*" -Include *.mp3, *.wav -File -ErrorAction SilentlyContinue
                foreach ($File in $Files) {
                    $DestPath = Join-Path $TargetDir $File.Name
                    Move-Item -LiteralPath $File.FullName -Destination $DestPath -Force
                    $Count++
                    Write-Host " -> SCARICATO: $($File.Name)" -ForegroundColor Cyan
                }
            }

            # Aggiorna l'ora esatta dentro MRECSET.txt (in formato ASCII puro per il microchip)
            if (Test-Path $ConfigFile) {
                $NowTime = (Get-Date).ToString("HH:mm yyyy/MM/dd")
                $RawText = [System.IO.File]::ReadAllText($ConfigFile)
                $UpdatedText = $RawText -replace "(?m)^TIME:.*$", "TIME:$NowTime"
                [System.IO.File]::WriteAllText($ConfigFile, $UpdatedText, [System.Text.Encoding]::ASCII)
                Write-Host "Orologio MRECSET.txt aggiornato a: TIME:$NowTime" -ForegroundColor Yellow
            }

            # Espulsione sicura della chiavetta da Windows
            Start-Sleep -Seconds 1
            $Shell = New-Object -ComObject Shell.Application
            $Shell.Namespace(17).ParseName($Drive.DeviceID).InvokeVerb("Eject")
            Write-Host "Chiavetta espulsa! Totale file scaricati: $Count" -ForegroundColor Green

            [console]::beep(1000, 200)
            [console]::beep(1500, 300)

            if ($BotToken -and ($BotToken -ne "INSERISCI_QUI_IL_TUO_TOKEN")) {
                $Msg = "Registratore USB Sincronizzato (da Windows)! File scaricati: $Count. Orologio aggiornato. Puoi staccare la chiavetta!"
                Invoke-RestMethod -Uri "https://api.telegram.org/bot$BotToken/sendMessage" -Method Post -Body @{chat_id=$ChatId; text=$Msg} -ErrorAction SilentlyContinue | Out-Null
            }

            $Voice.Speak("Registrazioni scaricate, puoi staccare la chiavetta!")
        }
    }
}

Unregister-Event -SourceIdentifier VolumeChange -ErrorAction SilentlyContinue
Remove-Event -SourceIdentifier VolumeChange -ErrorAction SilentlyContinue

Write-Host "=== SegretarIA USB Watcher attivo su Windows! ===" -ForegroundColor Yellow
Write-Host "Cartella destinazione: $TargetDir" -ForegroundColor Gray
Write-Host "Infila il registratore nella porta USB..." -ForegroundColor Yellow

Process-RecorderDrive

Register-WmiEvent -Class Win32_VolumeChangeEvent -SourceIdentifier VolumeChange -ErrorAction SilentlyContinue | Out-Null
while ($true) {
    $Event = Wait-Event -SourceIdentifier VolumeChange
    if ($Event.SourceEventArgs.NewEvent.EventType -eq 2) {
        Start-Sleep -Seconds 2
        Process-RecorderDrive
    }
    Remove-Event -SourceIdentifier VolumeChange -ErrorAction SilentlyContinue
}
