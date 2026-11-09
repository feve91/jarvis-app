# Jarvis Mobile - Buildozer Android Config
# =========================================================
# Para compilar:  buildozer android debug
# =========================================================

[app]
title = JARVIS AI
package.name = jarvaisai
package.domain = com.andresvelasquez.jarvis
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,mp3,wav,ogg,ttf,txt,db,ico
source.include_patterns = assets/*,assets/music/*,negocios/*,ui/*,service/*,DOCUMENTACION/*
source.exclude_dirs = tests,bin,.git,.venv,__pycache__,.buildozer
version = 2.5.0

# ----- Dependencias para Android -----
requirements = python3==3.11.5,hostpython3==3.11.5,kivy,requests,python-dateutil,certifi,urllib3,idna,charset-normalizer,plyer,pyjnius
# ----- Orientacion -----
orientation = portrait
fullscreen = 0

# ----- Icono y presplash -----
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/splash.png

# ----- Android -----
android.permissions = INTERNET, RECORD_AUDIO, RECEIVE_BOOT_COMPLETED, VIBRATE, POST_NOTIFICATIONS, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, ACCESS_NETWORK_STATE, WAKE_LOCK

android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.enable_androidx = True
android.accept_sdk_license = True
android.gradle_dependencies = androidx.core:core:1.12.0

# ----- Otras opciones -----
android.logcat_filters = *:S python:D
android.copy_libs = 1

[buildozer]
log_level = 2
warn_on_root = 1
p4a.branch = master
