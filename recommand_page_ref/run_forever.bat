@echo off
title Closing Price Dashboard Server
:start
echo [%time%] Starting Dashboard Server...
node server.js
echo [%time%] Server stopped/crashed. Restarting in 5 seconds...
timeout /t 5
goto start
