import os
import shutil
import threading
import base64
from config import SHARED_DIR

class FileManager:
    def __init__(self, operation_log):
        self.shared_dir = SHARED_DIR
        self.lock = threading.Lock()
        self.operation_log = operation_log
        self.offline_manager = None  # Se establecerá después de la inicialización
        
        # Asegurar que el directorio compartido existe
        os.makedirs(self.shared_dir, exist_ok=True)
    
    def set_offline_manager(self, offline_manager):
        """Establece el manager offline"""
        self.offline_manager = offline_manager
    
    def list_files(self):
        """Lista todos los archivos en el directorio compartido"""
        files = []
        with self.lock:
            for root, dirs, filenames in os.walk(self.shared_dir):
                relative_root = os.path.relpath(root, self.shared_dir)
                if relative_root == '.':
                    relative_root = ''
                
                for filename in filenames:
                    if filename in ['operations.log', 'offline_queue.json', 'sync_status.json']:
                        continue
                    
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.join(relative_root, filename)
                    
                    # Obtener información del archivo
                    stat = os.stat(full_path)
                    file_info = {
                        'name': relative_path,
                        'path': full_path,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'is_dir': False
                    }
                    
                    # Agregar estado de sincronización si está disponible
                    if self.offline_manager:
                        sync_status = self.offline_manager.get_sync_status(relative_path)
                        file_info['sync_status'] = sync_status
                    
                    files.append(file_info)
                
                for dirname in dirs:
                    full_path = os.path.join(root, dirname)
                    relative_path = os.path.join(relative_root, dirname)
                    
                    # Obtener información del directorio
                    stat = os.stat(full_path)
                    files.append({
                        'name': relative_path,
                        'path': full_path,
                        'size': 0,
                        'modified': stat.st_mtime,
                        'is_dir': True
                    })
            
        return files
    
    def get_file_data(self, filename):
        """Obtiene los datos de un archivo"""
        file_path = os.path.join(self.shared_dir, filename)
        
        if not os.path.exists(file_path):
            return None
        
        if os.path.isdir(file_path):
            return None
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        return base64.b64encode(file_data).decode('utf-8')
    
    def save_file(self, filename, file_data, is_base64=True, is_offline=False):
        """Guarda un archivo en el sistema"""
        file_path = os.path.join(self.shared_dir, filename)
        
        # Crear los directorios necesarios
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with self.lock:
            if is_base64:
                file_data = base64.b64decode(file_data)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Si es una operación offline, agregar a la cola
            if is_offline and self.offline_manager:
                self.offline_manager.add_to_offline_queue("save", filename, base64.b64encode(file_data).decode('utf-8'))
        
        return True
    
    def delete_file(self, filename, node_name, log_operation=True, is_offline=False):
        """Elimina un archivo o directorio del sistema"""
        file_path = os.path.join(self.shared_dir, filename)
        
        if not os.path.exists(file_path):
            return False
        
        with self.lock:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            
            if log_operation:
                self.operation_log.add_operation("delete", node_name, filename=filename)
            
            # Si es una operación offline, agregar a la cola
            if is_offline and self.offline_manager:
                self.offline_manager.add_to_offline_queue("delete", filename)
        
        return True
    
    def transfer_file(self, filename, target_node, source_node, file_data=None, log_operation=True, is_offline=False):
        """Prepara un archivo para transferir o registra una transferencia completada"""
        if file_data:
            # Estamos recibiendo un archivo
            return self.save_file(filename, file_data, is_offline=is_offline)
        else:
            # Estamos iniciando una transferencia
            file_data = self.get_file_data(filename)
            if file_data and log_operation:
                self.operation_log.add_operation("transfer", source_node, target_node=target_node, filename=filename)
            return file_data