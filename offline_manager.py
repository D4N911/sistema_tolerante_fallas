import json
import os
import time
import threading
from datetime import datetime

class OfflineManager:
    def __init__(self, file_manager, operation_log):
        self.file_manager = file_manager
        self.operation_log = operation_log
        self.lock = threading.Lock()
        self.offline_queue = []
        self.sync_status = {}  # Estado de sincronización de cada archivo
        self.offline_queue_file = "offline_queue.json"
        self.sync_status_file = "sync_status.json"
        
        # Cargar estado guardado
        self.load_state()
    
    def load_state(self):
        """Carga el estado guardado de la cola offline y estado de sincronización"""
        if os.path.exists(self.offline_queue_file):
            try:
                with open(self.offline_queue_file, 'r') as f:
                    self.offline_queue = json.load(f)
            except json.JSONDecodeError:
                self.offline_queue = []
        
        if os.path.exists(self.sync_status_file):
            try:
                with open(self.sync_status_file, 'r') as f:
                    self.sync_status = json.load(f)
            except json.JSONDecodeError:
                self.sync_status = {}
    
    def save_state(self):
        """Guarda el estado actual de la cola offline y estado de sincronización"""
        with open(self.offline_queue_file, 'w') as f:
            json.dump(self.offline_queue, f, indent=2)
        
        with open(self.sync_status_file, 'w') as f:
            json.dump(self.sync_status, f, indent=2)
    
    def add_to_offline_queue(self, operation_type, filename, data=None):
        """Agrega una operación a la cola offline"""
        operation = {
            "type": operation_type,
            "filename": filename,
            "timestamp": time.time(),
            "operation_id": f"{operation_type}_{filename}_{time.time()}",
            "data": data
        }
        
        with self.lock:
            self.offline_queue.append(operation)
            self.sync_status[filename] = {
                "synced": False,
                "last_modified": time.time(),
                "pending_operations": True
            }
            self.save_state()
        
        return operation
    
    def process_offline_queue(self):
        """Procesa la cola de operaciones offline"""
        with self.lock:
            operations_to_process = self.offline_queue.copy()
            self.offline_queue = []
        
        for operation in operations_to_process:
            try:
                if operation["type"] == "save":
                    self.file_manager.save_file(
                        operation["filename"],
                        operation["data"],
                        is_base64=True
                    )
                elif operation["type"] == "delete":
                    self.file_manager.delete_file(
                        operation["filename"],
                        "local",
                        log_operation=True
                    )
                
                # Marcar archivo como sincronizado
                self.sync_status[operation["filename"]] = {
                    "synced": True,
                    "last_modified": time.time(),
                    "pending_operations": False
                }
            except Exception as e:
                # Si hay error, volver a poner en la cola
                with self.lock:
                    self.offline_queue.append(operation)
        
        self.save_state()
    
    def get_sync_status(self, filename=None):
        """Obtiene el estado de sincronización de un archivo o todos los archivos"""
        with self.lock:
            if filename:
                return self.sync_status.get(filename, {
                    "synced": True,
                    "last_modified": 0,
                    "pending_operations": False
                })
            return self.sync_status.copy()
    
    def mark_as_synced(self, filename):
        """Marca un archivo como sincronizado"""
        with self.lock:
            if filename in self.sync_status:
                self.sync_status[filename]["synced"] = True
                self.sync_status[filename]["pending_operations"] = False
                self.save_state() 