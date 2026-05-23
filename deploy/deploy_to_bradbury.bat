@echo off
REM Deploy ConvenatContract.py to GenLayer Bradbury Testnet
REM Double-click this file or run from cmd/PowerShell
echo ============================================================
echo  Deploying ConvenatContract to GenLayer Bradbury Testnet
echo ============================================================
echo.

REM Check if genlayer CLI is available
where genlayer >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing genlayer CLI...
    npm install -g genlayer
)

REM Set network to Bradbury
echo [1/3] Setting network to Bradbury...
genlayer network testnet-bradbury

REM Deploy
echo [2/3] Deploying contract...
genlayer deploy --contract contracts\ConvenatContract.py

echo.
echo [3/3] Done!
echo.
echo Copy the contract address above into your .env file as:
echo   CONVENAT_CONTRACT_ADDRESS=0x...
echo.
pause
