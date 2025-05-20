#!/bin/bash

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado"
    echo "Por favor, ejecuta primero ./install_macos.sh o ./install_ubuntu.sh según tu sistema"
    exit 1
fi

# Verificar si los puertos están disponibles
if lsof -i :8080 &> /dev/null || lsof -i :9090 &> /dev/null; then
    echo "Error: Los puertos 8080 o 9090 ya están en uso"
    echo "Por favor, libera estos puertos o modifica config.py para usar otros puertos"
    exit 1
fi

# Instalar dependencias
pip3 install -r requirements.txt

# Crear directorio para archivos compartidos si no existe
mkdir -p ~/sistema_tolerante_fallas_files

# Verificar permisos del directorio
if [ ! -w ~/sistema_tolerante_fallas_files ]; then
    echo "Error: No hay permisos de escritura en ~/sistema_tolerante_fallas_files"
    echo "Por favor, verifica los permisos del directorio"
    exit 1
fi

# Iniciar la aplicación
python3 app.py 