# Build / Refresh & Deploy Script for NotebookLM-py

# Set location to NotebookLM-py repo
Set-Location 'C:\src\notebooklm-py'

# Deploy index.html + runtime-contract.json to LocalWP plugin
$pluginPath = 'C:\Users\jgoka\Local Sites\gaijinworld-local\app\public\wp-content\plugins\notebooklm-py'

# Ensure target plugin directory exists
New-Item -ItemType Directory -Path $pluginPath -Force | Out-Null

# Copy fresh index.html and runtime-contract.json
Copy-Item -Force "C:\src\notebooklm-py\index.html" "$pluginPath\index.html"
Copy-Item -Force "C:\src\notebooklm-py\runtime-contract.json" "$pluginPath\runtime-contract.json"

# Verify deployment via PHP CLI
$phpExe = 'C:\Users\jgoka\AppData\Roaming\Local\lightning-services\php-8.5.1+1\bin\win64\php.exe'
$extDir = 'C:\Users\jgoka\AppData\Roaming\Local\lightning-services\php-8.5.1+1\bin\win64\ext'
$iniContent = "extension_dir=`"$extDir`"`nextension=mysqli`nextension=curl`nextension=openssl`n"
$iniPath = Join-Path $env:TEMP 'nblm_verify.ini'
Set-Content -Path $iniPath -Value $iniContent -Encoding UTF8

$verifyScript = @'
<?php
$url = 'https://gaijinworld-local.local/notebooklm-py/';
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
echo "HTTP Code: $httpCode\n";
preg_match('/<title>(.*?)<\/title>/', $response, $titleMatch);
echo "Title: " . ($titleMatch[1] ?? 'N/A') . "\n";
preg_match('/"visibleVersion"\s*:\s*"([^"]+)"/', $response, $versionMatch);
echo "visibleVersion: " . ($versionMatch[1] ?? 'NOT FOUND') . "\n";
echo "runtimeConfigJson present: " . (strpos($response, 'runtimeConfigJson') !== false ? 'YES' : 'NO') . "\n";
'@
$verifyPath = Join-Path $env:TEMP 'nblm_verify.php'
Set-Content -Path $verifyPath -Value $verifyScript -Encoding UTF8
& $phpExe -c $iniPath $verifyPath

# Git commit and push
Set-Location 'C:\src\notebooklm-py'
git add -A
git commit -m "chore: bump visibleVersion to 2026.07.23.19 - deploy to LocalWP"
git push origin main

# Confirm live site in browser
Start-Process 'http://gaijinworld-local.local/notebooklm-py'
