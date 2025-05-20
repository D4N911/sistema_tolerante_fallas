#!/bin/bash

# Verificar si Homebrew está instalado
if ! command -v brew &> /dev/null; then
    echo "Instalando Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

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

# Instalar lsof para verificar puertos
if ! command -v lsof &> /dev/null; then
    echo "Instalando lsof..."
    brew install lsof
fi

# Instalar dependencias
pip3 install -r requirements.txt

# Crear directorio para archivos compartidos
mkdir -p ~/sistema_tolerante_fallas_files

# Dar permisos de ejecución a start.sh
chmod +x start.sh

echo "Instalación completada. Ahora puedes ejecutar ./start.sh" 