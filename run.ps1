# Stop any process using port 8081
$port = 8081
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($process) {
    $process.ProcessId | ForEach-Object { Stop-Process -Id $_ -Force }
}

# Wait a moment for processes to terminate
Start-Sleep -Seconds 2

# Start the Spring Boot application
mvn spring-boot:run
