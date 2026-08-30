@echo off
chcp 65001 >nul

echo VoiceAIAssistant をセットアップします。
uv sync --extra cuda

echo Irodori-TTS-Server をセットアップします。
git clone https://github.com/Aratako/Irodori-TTS-Server
cd Irodori-TTS-Server
uv sync --extra cu128
copy .env.example .env
cd ..
copy voices\chara1.wav Irodori-TTS-Server\voices
copy voices\chara2.wav Irodori-TTS-Server\voices

echo llama.cpp をセットアップします。
set "URL1=https://github.com/ggml-org/llama.cpp/releases/download/b10679/llama-b10679-bin-win-cuda-12.4-x64.zip"
set "ZIP_FILE1=%~dp0llama-b10679-bin-win-cuda-12.4-x64.zip"
set "URL2=https://github.com/ggml-org/llama.cpp/releases/download/b10679/cudart-llama-bin-win-cuda-12.4-x64.zip"
set "ZIP_FILE2=%~dp0cudart-llama-bin-win-cuda-12.4-x64.zip"

set "DEST_DIR=%~dp0llamacpp"

powershell -Command "Invoke-WebRequest -Uri '%URL1%' -OutFile '%ZIP_FILE1%'"
powershell -Command "Expand-Archive -Path '%ZIP_FILE1%' -DestinationPath '%DEST_DIR%' -Force"

powershell -Command "Invoke-WebRequest -Uri '%URL1%' -OutFile '%ZIP_FILE1%'"
powershell -Command "Expand-Archive -Path '%ZIP_FILE1%' -DestinationPath '%DEST_DIR%' -Force"

:: zipの削除（クリーンアップ）
del "%ZIP_FILE1%" "%ZIP_FILE2%"

echo 完了しました。