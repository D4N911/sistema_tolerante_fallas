import threading
import time
from file_manager import FileManager
from operation_log import OperationLog
from network import NetworkManager
from sync import SyncManager
from offline_manager import OfflineManager
from config import NODE_NAME

class Node:
    
    def __init__(self):
        self.node_name = NODE_NAME
        
        # Inicializar componentes
        self.operation_log = OperationLog()
        self.file_manager = FileManager(self.operation_log)
        self.offline_manager = OfflineManager(self.file_manager, self.operation_log)
        self.sync_manager = SyncManager(self.file_manager, self.operation_log)
        self.network_manager = NetworkManager(self.file_manager, self.operation_log, self.sync_manager)
        
        # Establecer referencias circulares
        self.sync_manager.set_network_manager(self.network_manager)
        self.file_manager.set_offline_manager(self.offline_manager)
        
        # Iniciar sincronización periódica
        self.sync_thread = threading.Thread(target=self._periodic_sync)
        self.sync_thread.daemon = True
        self.running = True
    
    def start(self):
        """Inicia todos los servicios del nodo"""
        print(f"Iniciando nodo: {self.node_name}")
        
        # Iniciar manager de red
        self.network_manager.start()
        
        # Iniciar sincronización periódica
        self.sync_thread.start()
        
        print(f"Nodo {self.node_name} iniciado correctamente")
    
    def _periodic_sync(self):
        """Realiza sincronización periódica con otros nodos"""
        while self.running:
            try:
                # Esperar un tiempo antes de sincronizar
                time.sleep(30)  # Sincronizar cada 30 segundos
                
                # Procesar cola offline
                self.offline_manager.process_offline_queue()
                
                # Iniciar sincronización
                self.sync_manager.start_sync()
            except Exception as e:
                print(f"Error durante la sincronización periódica: {e}")
    
    def list_files(self):
        """Lista los archivos en el sistema"""
        return self.file_manager.list_files()
    
    def transfer_file(self, filename, target_node, is_offline=False):
        """Transfiere un archivo a otro nodo"""
        return self.network_manager.send_file(filename, target_node, is_offline=is_offline)
    
    def delete_file(self, filename, is_offline=False):
        """Elimina un archivo del sistema"""
        return self.network_manager.delete_file(filename, is_offline=is_offline)
    
    def get_node_status(self):
        """Obtiene el estado de conexión de todos los nodos"""
        status = self.network_manager.get_node_status()
        status[self.node_name] = True  # Este nodo siempre está activo
        return status
    
    def stop(self):
        """Detiene todos los servicios del nodo"""
        self.running = False
        self.network_manager.stop()
        print(f"Nodo {self.node_name} detenido")

    def get_remote_files(self, target_node):
        """Obtiene la lista de archivos de un nodo remoto"""
        try:
            message = {
                "type": "list_files",
                "source_node": self.node_name,
                "timestamp": time.time()
            }
            
            response = self.network_manager._send_message(target_node, message)
            
            if isinstance(response, dict) and response.get("status") == "ok":
                return response.get("files", [])
            return None
        except Exception as e:
            print(f"Error al obtener archivos remotos: {e}")
            return None
    
    