@echo off
chcp 65001 >nul

echo Setup VoiceAIAssistant
uv sync --extra cuda

echo Setup Irodori-TTS-Server
git clone https://github.com/Aratako/Irodori-TTS-Server
cd Irodori-TTS-Server
uv sync --extra cu128
copy .env.example .env
cd ..
copy voices\chara1.wav Irodori-TTS-Server\voices
copy voices\chara2.wav Irodori-TTS-Server\voices

echo Setup llama.cpp
set "URL1=https://github.com/ggml-org/llama.cpp/releases/download/b10679/llama-b10679-bin-win-cuda-12.4-x64.zip"
set "ZIP_FILE1=%~dp0llama-b10679-bin-win-cuda-12.4-x64.zip"
set "URL2=https://github.com/ggml-org/llama.cpp/releases/download/b10679/cudart-llama-bin-win-cuda-12.4-x64.zip"
set "ZIP_FILE2=%~dp0cudart-llama-bin-win-cuda-12.4-x64.zip"

set "DEST_DIR=%~dp0llamacpp"

:: curl.exe で高速取得（-L: リダイレクト追従, -o: 保存先指定）
echo Downloading llama.cpp binaries...
curl.exe -L -o "%ZIP_FILE1%" "%URL1%"
curl.exe -L -o "%ZIP_FILE2%" "%URL2%"

:: 解凍処理
echo Extracting files...
powershell -Command "Expand-Archive -Path '%ZIP_FILE1%' -DestinationPath '%DEST_DIR%' -Force"
powershell -Command "Expand-Archive -Path '%ZIP_FILE2%' -DestinationPath '%DEST_DIR%' -Force"

:: zipの削除（クリーンアップ）
del "%ZIP_FILE1%" "%ZIP_FILE2%"

echo Done
