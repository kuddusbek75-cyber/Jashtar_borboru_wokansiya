$ErrorActionPreference = "Stop"

python --version | Out-Null

if (!(Test-Path ".\venv")) {
    python -m venv venv
}

Set-ExecutionPolicy Unrestricted -Scope Process -Force
& .\venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install Django Pillow

if (!(Test-Path ".\manage.py")) {
    django-admin startproject config .
}

if (!(Test-Path ".\core")) {
    python manage.py startapp core
}

# core/templates + empty index.html
if (!(Test-Path ".\core\templates")) {
    New-Item -ItemType Directory -Path ".\core\templates" | Out-Null
}
if (!(Test-Path ".\core\templates\index.html")) {
    New-Item -ItemType File -Path ".\core\templates\index.html" | Out-Null
}

# core/urls.py WITHOUT views
$coreUrlsPath = ".\core\urls.py"
$coreUrlsContent = @"
from django.urls import path

urlpatterns = [
]
"@
Set-Content -Path $coreUrlsPath -Value $coreUrlsContent -Encoding UTF8

# Find config/settings.py
$settingsFile = Get-ChildItem -Path . -Recurse -File -Filter settings.py |
    Where-Object { $_.FullName -match "\\config\\settings\.py$" } |
    Select-Object -First 1

if (-not $settingsFile) { throw "settings.py not found" }

$settings = Get-Content $settingsFile.FullName -Raw

# Remove docstrings
$settings = $settings -replace '"""[\s\S]*?"""', ''

# Remove full-line comments
$settings = ($settings -split "`n") | Where-Object { $_ -notmatch "^\s*#" }
$settings = $settings -join "`n"

# Add 'core' to END of INSTALLED_APPS
if ($settings -notmatch "'core'") {
    $start = $settings.IndexOf("INSTALLED_APPS")
    if ($start -lt 0) { throw "INSTALLED_APPS not found" }

    $open = $settings.IndexOf("[", $start)
    if ($open -lt 0) { throw "INSTALLED_APPS '[' not found" }

    $close = $settings.IndexOf("]", $open)
    if ($close -lt 0) { throw "INSTALLED_APPS ']' not found" }

    $before = $settings.Substring(0, $close)
    $after  = $settings.Substring($close)

    if ($before -notmatch "`n\s*$") { $before += "`r`n" }

    $settings = $before + "    'core',`r`n" + $after
}

# Internationalization
$settings = $settings -replace "LANGUAGE_CODE\s*=\s*'.*?'", "LANGUAGE_CODE = 'ru-ru'"
$settings = $settings -replace "TIME_ZONE\s*=\s*'.*?'", "TIME_ZONE = 'Asia/Bishkek'"
$settings = $settings -replace "USE_I18N\s*=\s*.*", "USE_I18N = True"
$settings = $settings -replace "USE_TZ\s*=\s*.*", "USE_TZ = True"

# Force STATIC/MEDIA block exactly as you want
$staticMediaBlock = @"

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'staticfiles_dev']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'
"@

# Remove existing STATIC/MEDIA lines if present (to avoid duplicates)
$settings = $settings -replace "(?m)^\s*STATIC_URL\s*=.*\r?\n", ""
$settings = $settings -replace "(?m)^\s*STATIC_ROOT\s*=.*\r?\n", ""
$settings = $settings -replace "(?m)^\s*STATICFILES_DIRS\s*=.*\r?\n", ""
$settings = $settings -replace "(?m)^\s*MEDIA_URL\s*=.*\r?\n", ""
$settings = $settings -replace "(?m)^\s*MEDIA_ROOT\s*=.*\r?\n", ""

# Also remove the default Django "Static files ..." header if it survived (just in case)
$settings = $settings -replace "(?m)^\s*Static files.*\r?\n", ""
$settings = $settings -replace "(?m)^\s*Media files.*\r?\n", ""

# Append the clean block at end
$settings = $settings.TrimEnd() + $staticMediaBlock + "`r`n"

Set-Content -Path $settingsFile.FullName -Value $settings -Encoding UTF8

# Replace config/urls.py fully (your exact code)
$configUrlsFile = Get-ChildItem -Path . -Recurse -File -Filter urls.py |
    Where-Object { $_.FullName -match "\\config\\urls\.py$" } |
    Select-Object -First 1

if (-not $configUrlsFile) { throw "config/urls.py not found" }

$configUrlsContent = @"
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"@
Set-Content -Path $configUrlsFile.FullName -Value $configUrlsContent -Encoding UTF8

pip freeze | Out-File -Encoding utf8 requirements.txt

Write-Host ""
Write-Host "Done."
Write-Host "Run:"
Write-Host "python manage.py migrate"
Write-Host "python manage.py runserver"