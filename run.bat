@echo off
:: Kill any process running on port 8081
taskkill /F /IM java.exe

:: Wait a moment for the process to terminate
timeout /t 2 /nobreak >nul

:: Start the Spring Boot application
call mvn spring-boot:run
