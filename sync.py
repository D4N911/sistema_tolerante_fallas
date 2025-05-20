import threading
import time

class SyncManager:
    def __init__(self, file_manager, operation_log):
        self.file_manager = file_manager
        self.operation_log = operation_log
        self.network_manager = None  # Se establecerá después
        self.lock = threading.Lock()
        self.syncing = False
    
    def set_network_manager(self, network_manager):
        self.network_manager = network_manager
    
    def start_sync(self):
        """Inicia el proceso de sincronización con otros nodos"""
        with self.lock:
            if self.syncing:
                return
            self.syncing = True
        
        try:
            # Obtener el último timestamp de operación registrado
            last_timestamp = self.operation_log.get_last_timestamp()
            
            # Solicitar operaciones a todos los nodos activos
            node_status = self.network_manager.get_node_status()
            
            for node, alive in node_status.items():
                # No intentar sincronizar con uno mismo o con nodos inactivos
                if node != self.network_manager.node_name and alive:
                    self._sync_with_node(node, last_timestamp)
            
        finally:
            with self.lock:
                self.syncing = False
    
    def _sync_with_node(self, node, last_timestamp):
        """Sincroniza operaciones con un nodo específico"""
        # No intentar sincronizar con uno mismo
        if node == self.network_manager.node_name:
            return
        
        message = {
            "type": "sync_request",
            "source_node": self.network_manager.node_name,
            "last_timestamp": last_timestamp
        }
        
        response = self.network_manager._send_message(node, message)
        
        # Verificar que la respuesta sea un diccionario (no None o True)
        if isinstance(response, dict) and response.get("status") == "ok":
            operations = response.get("operations", [])
            
            # Aplicar operaciones en orden cronológico
            operations.sort(key=lambda op: op["timestamp"])
            
            for operation in operations:
                if not self.operation_log.operation_exists(operation["operation_id"]):
                    self.apply_operation(operation)
    
    def apply_operation(self, operation):
        """Aplica una operación de sincronización"""
        operation_type = operation.get("type")
        source_node = operation.get("source_node")
        filename = operation.get("filename")
        timestamp = operation.get("timestamp")
        
        if operation_type == "delete":
            # Aplicar eliminación
            self.file_manager.delete_file(filename, source_node, log_operation=False)
            
            # Registrar en el log local
            if not self.operation_log.operation_exists(operation["operation_id"]):
                self.operation_log.add_operation(
                    "delete", source_node, filename=filename, timestamp=timestamp
                )
        
        elif operation_type == "transfer":
            target_node = operation.get("target_node")
            
            # Solo aplicar si somos el destino o el origen
            if target_node == self.network_manager.node_name:
                # Solicitar el archivo actual al nodo origen
                request_message = {
                    "type": "get_file",
                    "source_node": self.network_manager.node_name,
                    "filename": filename
                }
                
                response = self.network_manager._send_message(source_node, request_message)
                
                # Asegurarse de que la respuesta sea un diccionario
                if isinstance(response, dict) and response.get("status") == "ok":
                    file_data = response.get("file_data")
                    if file_data:
                        self.file_manager.save_file(filename, file_data)
                
                # Registrar en el log local
                if not self.operation_log.operation_exists(operation["operation_id"]):
                    self.operation_log.add_operation(
                        "transfer", source_node, target_node=target_node, 
                        filename=filename, timestamp=timestamp
                    )