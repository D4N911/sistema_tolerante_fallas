from flask import Flask, render_template, request, jsonify
import os
import threading
from node import Node
from config import WEB_PORT, NODES

app = Flask(__name__)
node = Node()

@app.route('/api/node_files/<node_name>', methods=['GET'])
def get_node_files(node_name):
    """API para obtener archivos de un nodo específico"""
    if node_name == node.node_name:
        # Si es el nodo local, usar la función existente
        files = node.list_files()
        return jsonify(files)
    else:
        # Si es otro nodo, solicitar los archivos a través de la red
        files = node.get_remote_files(node_name)
        if files is None:
            return jsonify([])
        return jsonify(files)
    
@app.route('/')
def index():
    """Página principal de la interfaz web"""
    return render_template('index.html', node_name=node.node_name, nodes=NODES)

@app.route('/api/files', methods=['GET'])
def list_files():
    """API para listar archivos"""
    files = node.list_files()
    return jsonify(files)

@app.route('/api/transfer', methods=['POST'])
def transfer_file():
    """API para transferir un archivo"""
    data = request.get_json()
    filename = data.get('filename')
    target_node = data.get('target_node')
    
    if not filename or not target_node:
        return jsonify({"status": "error", "message": "Faltan parámetros"})
    
    success = node.transfer_file(filename, target_node)
    
    if success:
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Error al transferir archivo"})

@app.route('/api/delete', methods=['POST'])
def delete_file():
    """API para eliminar un archivo"""
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"status": "error", "message": "Falta nombre de archivo"})
    
    success = node.delete_file(filename)
    
    if success:
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Error al eliminar archivo"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """API para obtener el estado de los nodos"""
    status = node.get_node_status()
    return jsonify(status)

def start_node():
    """Inicia el nodo en un thread separado"""
    node.start()

if __name__ == '__main__':
    # Iniciar el nodo en un thread separado
    node_thread = threading.Thread(target=start_node)
    node_thread.daemon = True
    node_thread.start()
    
    print(f"Iniciando nodo {node.node_name} en http://0.0.0.0:{WEB_PORT}")
    print("Presiona CTRL+C para detener la app")
    # Iniciar la aplicación web
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False)