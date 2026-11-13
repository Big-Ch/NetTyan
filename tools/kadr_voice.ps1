param([Parameter(Mandatory=$true)][string]$TextPath,
      [Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = @($speech.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
    if ($voices -contains 'Microsoft Pavel') { $speech.SelectVoice('Microsoft Pavel') }
    elseif ($voices -contains 'Microsoft Irina Desktop') { $speech.SelectVoice('Microsoft Irina Desktop') }
    else { throw 'No Russian Windows speech voice installed' }
    $speech.Rate = 0
    $speech.SetOutputToWaveFile($OutputPath)
    $speech.Speak([System.IO.File]::ReadAllText($TextPath, [System.Text.Encoding]::UTF8))
    $speech.SetOutputToNull()
} finally {
    $speech.Dispose()
}
