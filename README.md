# Sistema Tolerante a Fallas

Sistema distribuido que permite la sincronización de archivos entre múltiples nodos, con soporte para operaciones offline y recuperación automática.

## Características

- Sincronización automática entre nodos
- Soporte para operaciones offline
- Interfaz web para gestión de archivos
- Recuperación automática de fallos
- Sistema de colas para operaciones pendientes

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Acceso a la red entre nodos

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/D4N911/sistema_tolerante_fallas.git
cd sistema_tolerante_fallas
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar el nodo:
   - Abrir `config.py`
   - Cambiar `THIS_NODE` al nombre de tu nodo (ej: "MacOS1", "MacOS2", "Ubuntu1", "Ubuntu2")
   - Verificar que la IP configurada sea correcta

## Configuración de Nodos

El sistema soporta los siguientes nodos:
- MacOS1 (IP: 172.26.163.109)
- MacOS2 (IP: 172.26.167.45)
- Ubuntu1 (IP: 172.31.1.164)
- Ubuntu2 (IP: 172.25.181.66)

Cada nodo debe tener una configuración única en `config.py`.

## Uso

1. Iniciar el nodo:
```bash
./start.sh
```

2. Acceder a la interfaz web:
   - Abrir un navegador
   - Ir a `http://localhost:8080`

## Operaciones Disponibles

- **Transferir archivos**: Seleccionar archivo y nodo destino
- **Eliminar archivos**: Seleccionar archivo y confirmar eliminación
- **Ver estado**: Monitorear estado de nodos y sincronización
- **Operaciones offline**: El sistema mantiene una cola de operaciones pendientes

## Estructura de Archivos

- `app.py`: Aplicación web principal
- `node.py`: Lógica del nodo
- `network.py`: Manejo de comunicación entre nodos
- `file_manager.py`: Gestión de archivos
- `sync.py`: Sincronización entre nodos
- `offline_manager.py`: Manejo de operaciones offline
- `config.py`: Configuración del sistema

## Solución de Problemas

1. **Nodo no aparece en la interfaz**:
   - Verificar que el nodo esté en ejecución
   - Comprobar la configuración de IP en `config.py`
   - Verificar que los puertos 8080 y 9090 estén disponibles

2. **Archivos no se sincronizan**:
   - Verificar conexión entre nodos
   - Comprobar logs en `sistema.log`
   - Verificar estado de sincronización en la interfaz

3. **Error al transferir archivos**:
   - Verificar espacio en disco
   - Comprobar permisos de escritura
   - Verificar tamaño del archivo (límite: 10MB)

## Contribución

1. Crear una rama para tu feature:
```bash
git checkout -b feature/nueva-funcionalidad
```

2. Hacer commit de tus cambios:
```bash
git add .
git commit -m "Descripción de los cambios"
```

3. Hacer push a tu rama:
```bash
git push origin feature/nueva-funcionalidad
```

4. Crear un Pull Request en GitHub

## Contacto

Para reportar problemas o sugerir mejoras, crear un Issue en GitHub. 