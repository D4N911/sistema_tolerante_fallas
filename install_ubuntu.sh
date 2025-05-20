#!/bin/bash

# Actualizar lista de paquetes
sudo apt-get update

# Instalar Python y pip si no están instalados
if ! command -v python3 &> /dev/null; then
    echo "Instalando Python 3..."
    sudo apt-get install -y python3
fi

if ! command -v pip3 &> /dev/null; then
    echo "Instalando pip3..."
    sudo apt-get install -y python3-pip
fi

# Instalar dependencias del sistema
sudo apt-get install -y python3-dev build-essential lsof

# Instalar dependencias de Python
pip3 install -r requirements.txt

# Crear directorio para archivos compartidos
mkdir -p ~/sistema_tolerante_fallas_files

# Dar permisos de ejecución a start.sh
chmod +x start.sh

echo "Instalación completada. Ahora puedes ejecutar ./start.sh" 