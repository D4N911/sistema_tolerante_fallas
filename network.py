import socket
import threading
import json
import time
import base64
import struct
import logging
import atexit
from config import NODES, NODE_NAME, NETWORK_PORT, HEARTBEAT_INTERVAL, NODE_TIMEOUT, NETWORK_TIMEOUT, MAX_RETRIES, MAX_DIRECT_TRANSFER_SIZE

logger = logging.getLogger('sistema.network')

class NetworkManager:
    def __init__(self, file_manager, operation_log, sync_manager):
        self.nodes = NODES
        self.node_name = NODE_NAME
        self.port = NETWORK_PORT
        self.file_manager = file_manager
        self.operation_log = operation_log
        self.sync_manager = sync_manager
        
        # Estado de los nodos
        self.node_status = {node: {"alive": True, "last_seen": time.time()} 
                            for node in self.nodes if node != self.node_name}
        
        # Lock para acceso seguro al estado de los nodos
        self.status_lock = threading.Lock()
        
        # Iniciar servidor y mecanismos de heartbeat
        self.server_socket = None
        self.running = True
        self.active_connections = set()
        
        # Iniciar threads de servidor y heartbeat
        self.server_thread = threading.Thread(target=self._start_server)
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeats)
        self.status_thread = threading.Thread(target=self._check_nodes_status)
        
        self.server_thread.daemon = True
        self.heartbeat_thread.daemon = True
        self.status_thread.daemon = True
        
        # Registrar limpieza al cerrar
        atexit.register(self.stop)
        
        logger.info(f"Inicializando NetworkManager para nodo {self.node_name}")
        logger.info(f"Puerto de red: {self.port}")
        logger.info(f"Nodos configurados: {list(self.nodes.keys())}")
    
    def start(self):
        """Inicia los threads de red"""
        logger.info("Iniciando threads de red...")
        self.server_thread.start()
        self.heartbeat_thread.start()
        self.status_thread.start()
        logger.info("Threads de red iniciados")
    
    def _start_server(self):
        """Inicia el servidor para escuchar mensajes de otros nodos"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(10)
            
            logger.info(f"Servidor iniciado en el puerto {self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.debug(f"Conexión aceptada de {address}")
                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket, address))
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        logger.error(f"Error al aceptar conexión: {e}")
        except Exception as e:
            logger.error(f"Error al iniciar servidor: {e}")
            raise
    
    def _cleanup_connection(self, sock):
        """Limpia una conexión de socket"""
        try:
            if sock in self.active_connections:
                self.active_connections.remove(sock)
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            sock.close()
    
    def _send_message(self, node, message, retry_count=0):
        """Envía un mensaje a otro nodo con reintentos"""
        client_socket = None
        try:
            if node == self.node_name:
                logger.debug("Ignorando envío de mensaje a nosotros mismos")
                return True
            
            ip = self.nodes[node]["ip"]
            port = NETWORK_PORT
            
            logger.debug(f"Conectando a {node} ({ip}:{port})")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(NETWORK_TIMEOUT)
            client_socket.connect((ip, port))
            
            # Serializar el mensaje
            message_data = json.dumps(message).encode('utf-8')
            
            # Enviar longitud del mensaje primero (4 bytes)
            message_length = len(message_data)
            client_socket.sendall(struct.pack('!I', message_length))
            
            # Enviar el mensaje
            client_socket.sendall(message_data)
            
            # Recibir respuesta
            response_length = struct.unpack('!I', client_socket.recv(4))[0]
            response_data = client_socket.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            logger.debug(f"Respuesta recibida de {node}: {response}")
            return response
        except socket.timeout:
            logger.error(f"Timeout al conectar con {node}")
            if retry_count < MAX_RETRIES:
                logger.info(f"Reintentando conexión con {node} (intento {retry_count + 1})")
                time.sleep(1)  # Esperar antes de reintentar
                return self._send_message(node, message, retry_count + 1)
            with self.status_lock:
                self.node_status[node]["alive"] = False
            return None
        except ConnectionRefusedError:
            logger.error(f"Conexión rechazada por {node}")
            if retry_count < MAX_RETRIES:
                logger.info(f"Reintentando conexión con {node} (intento {retry_count + 1})")
                time.sleep(1)
                return self._send_message(node, message, retry_count + 1)
            with self.status_lock:
                self.node_status[node]["alive"] = False
            return None
        except Exception as e:
            logger.error(f"Error al enviar mensaje a {node}: {e}")
            if retry_count < MAX_RETRIES:
                logger.info(f"Reintentando conexión con {node} (intento {retry_count + 1})")
                time.sleep(1)
                return self._send_message(node, message, retry_count + 1)
            with self.status_lock:
                self.node_status[node]["alive"] = False
            return None
        finally:
            if client_socket:
                self._cleanup_connection(client_socket)
    
    def _handle_client(self, client_socket, address):
        """Maneja una conexión entrante de otro nodo"""
        self.active_connections.add(client_socket)
        try:
            logger.debug(f"Manejando conexión de {address}")
            
            # Recibir longitud del mensaje primero
            length_data = client_socket.recv(4)
            if not length_data:
                logger.warning(f"Conexión cerrada por {address} sin datos")
                return
            
            message_length = struct.unpack('!I', length_data)[0]
            logger.debug(f"Esperando mensaje de {message_length} bytes")
            
            # Recibir el mensaje completo
            chunks = []
            bytes_received = 0
            while bytes_received < message_length:
                chunk = client_socket.recv(min(message_length - bytes_received, 4096))
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            message_data = b''.join(chunks)
            message = json.loads(message_data.decode('utf-8'))
            logger.debug(f"Mensaje recibido de {address}: {message}")
            
            # Procesar mensaje
            response = self._process_message(message)
            logger.debug(f"Enviando respuesta a {address}: {response}")
            
            # Enviar respuesta
            response_data = json.dumps(response).encode('utf-8')
            response_length = len(response_data)
            client_socket.sendall(struct.pack('!I', response_length))
            client_socket.sendall(response_data)
            
        except Exception as e:
            logger.error(f"Error al manejar cliente {address}: {e}")
        finally:
            self._cleanup_connection(client_socket)
    
    def _process_message(self, message):
        """Procesa un mensaje recibido de otro nodo"""
        message_type = message.get("type")
        source_node = message.get("source_node")
        
        logger.debug(f"Procesando mensaje tipo {message_type} de {source_node}")
        
        # Actualizar estado del nodo
        if source_node and source_node in self.node_status:
            with self.status_lock:
                self.node_status[source_node]["alive"] = True
                self.node_status[source_node]["last_seen"] = time.time()
                logger.debug(f"Estado actualizado para nodo {source_node}")
        
        if message_type == "heartbeat":
            return {"status": "ok"}
        
        elif message_type == "transfer_file":
            filename = message.get("filename")
            file_data = message.get("file_data")
            
            logger.info(f"Recibiendo archivo {filename} de {source_node}")
            if self.file_manager.save_file(filename, file_data):
                # Registrar operación en el log
                self.operation_log.add_operation(
                    "transfer", source_node, target_node=self.node_name, 
                    filename=filename, timestamp=message.get("timestamp")
                )
                logger.info(f"Archivo {filename} guardado exitosamente")
                return {"status": "ok"}
            else:
                logger.error(f"Error al guardar archivo {filename}")
                return {"status": "error", "message": "Error al guardar archivo"}
        
        elif message_type == "delete_file":
            filename = message.get("filename")
            
            logger.info(f"Eliminando archivo {filename} por solicitud de {source_node}")
            if self.file_manager.delete_file(filename, source_node, log_operation=False):
                # Registrar operación en el log
                self.operation_log.add_operation(
                    "delete", source_node, filename=filename,
                    timestamp=message.get("timestamp")
                )
                logger.info(f"Archivo {filename} eliminado exitosamente")
                return {"status": "ok"}
            else:
                logger.error(f"Error al eliminar archivo {filename}")
                return {"status": "error", "message": "Error al eliminar archivo"}
        
        elif message_type == "sync_request":
            last_timestamp = message.get("last_timestamp", 0)
            operations = self.operation_log.get_operations_since(last_timestamp)
            logger.debug(f"Enviando {len(operations)} operaciones a {source_node}")
            return {"status": "ok", "operations": operations}
        
        elif message_type == "sync_operation":
            operation = message.get("operation")
            logger.debug(f"Aplicando operación de sincronización de {source_node}")
            self.sync_manager.apply_operation(operation)
            return {"status": "ok"}
        
        elif message_type == "list_files":
            files = self.file_manager.list_files()
            logger.debug(f"Enviando lista de {len(files)} archivos a {source_node}")
            return {"status": "ok", "files": files}
        
        else:
            logger.warning(f"Tipo de mensaje desconocido: {message_type}")
            return {"status": "error", "message": "Tipo de mensaje desconocido"}
    
    def _send_heartbeats(self):
        """Envía mensajes de heartbeat periódicamente a todos los nodos"""
        while self.running:
            for node in self.nodes:
                if node != self.node_name:
                    message = {
                        "type": "heartbeat",
                        "source_node": self.node_name,
                        "timestamp": time.time()
                    }
                    
                    logger.debug(f"Enviando heartbeat a {node}")
                    threading.Thread(target=self._send_message, args=(node, message)).start()
            
            time.sleep(HEARTBEAT_INTERVAL)
    
    def _check_nodes_status(self):
        """Verifica el estado de los nodos periódicamente"""
        while self.running:
            current_time = time.time()
            
            with self.status_lock:
                for node, status in self.node_status.items():
                    if status["alive"] and current_time - status["last_seen"] > NODE_TIMEOUT:
                        status["alive"] = False
                        logger.warning(f"Nodo {node} ha dejado de responder")
            
            time.sleep(HEARTBEAT_INTERVAL)
    
    def send_file(self, filename, target_node, is_offline=False):
        """Envía un archivo a otro nodo"""
        try:
            # Obtener datos del archivo
            file_data = self.file_manager.get_file_data(filename)
            if not file_data:
                return False
            
            # Si es una operación offline, guardar localmente y agregar a la cola
            if is_offline:
                self.file_manager.save_file(filename, file_data, is_offline=True)
                return True
            
            # Verificar tamaño del archivo
            file_size = len(base64.b64decode(file_data))
            if file_size > MAX_DIRECT_TRANSFER_SIZE:
                logger.warning(f"Archivo {filename} demasiado grande para transferencia directa")
                return False
            
            # Enviar archivo a través de la red
            message = {
                "type": "transfer_file",
                "source_node": self.node_name,
                "target_node": target_node,
                "filename": filename,
                "file_data": file_data,
                "timestamp": time.time()
            }
            
            response = self._send_message(target_node, message)
            if response and response.get("status") == "ok":
                # Marcar archivo como sincronizado
                if hasattr(self.file_manager, 'offline_manager'):
                    self.file_manager.offline_manager.mark_as_synced(filename)
                return True
            return False
        except Exception as e:
            logger.error(f"Error al enviar archivo: {e}")
            return False
    
    def delete_file(self, filename, is_offline=False):
        """Elimina un archivo del sistema"""
        try:
            # Si es una operación offline, eliminar localmente y agregar a la cola
            if is_offline:
                return self.file_manager.delete_file(filename, self.node_name, is_offline=True)
            
            # Eliminar archivo localmente
            success = self.file_manager.delete_file(filename, self.node_name)
            if not success:
                return False
            
            # Notificar a otros nodos
            message = {
                "type": "delete_file",
                "source_node": self.node_name,
                "filename": filename,
                "timestamp": time.time()
            }
            
            for node in self.nodes:
                if node != self.node_name:
                    try:
                        self._send_message(node, message)
                    except:
                        pass  # Ignorar errores de nodos no disponibles
            
            return True
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")
            return False
    
    def get_node_status(self):
        """Obtiene el estado de conexión de todos los nodos"""
        with self.status_lock:
            status = {node: info["alive"] for node, info in self.node_status.items()}
            status[self.node_name] = True  # Este nodo siempre está activo
            return status
    
    def stop(self):
        """Detiene todos los servicios del nodo"""
        logger.info("Deteniendo NetworkManager...")
        self.running = False
        
        # Limpiar todas las conexiones activas
        for sock in list(self.active_connections):
            self._cleanup_connection(sock)
        
        if self.server_socket:
            self._cleanup_connection(self.server_socket)
        
        logger.info("NetworkManager detenido")