#!/bin/bash

# Instalar Python si no está instalado
if ! command -v python3 &> /dev/null; then
    echo "Instalando Python 3..."
    brew install python3
fi

# Instalar pip si no está instalado
if ! command -v pip3 &> /dev/null; then
    echo "Instalando pip3..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# Instalar dependencias
pip3 install -r requirements.txt

# Crear directorio para archivos compartidos
mkdir -p ~/sistema_tolerante_fallas_files

echo "Instalación completada. Ahora puedes ejecutar ./start.sh" 