#!/bin/bash

# Instalar dependencias
pip3 install -r requirements.txt

# Crear directorio para archivos compartidos si no existe
mkdir -p ~/sistema_tolerante_fallas_files

# Iniciar la aplicación
python3 app.py 