import queue
import socket
import threading
import traceback

import bpy  # type: ignore

from ..handlers.binary_handler import BinaryHandler


class UDPServerManager:
    def __init__(self, uuid):
        self.uuid = uuid
        self.connection = next(
            (conn for conn in bpy.context.scene.portal_connections if conn.uuid == self.uuid),
            None,
        )
        self.data_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        self._server_thread = None
        self._sock = None
        self.error = None
        self.traceback = None
        self.error_lock = threading.Lock()

    def udp_handler(self):
        while not self.shutdown_event.is_set():
            try:
                # 1500 is the max size of a UDP packet
                data, addr = self._sock.recvfrom(1500)
                header = BinaryHandler.parse_header(data)
                payload = data[header.get_expected_size() + 2 :]
                if header.is_compressed:
                    payload = BinaryHandler.decompress(payload)
                if header.is_encrypted:
                    raise NotImplementedError("Encrypted data is not supported.")
                self.data_queue.put(payload.decode("utf-8"))
            except socket.timeout:
                continue
            except Exception as e:
                with self.error_lock:
                    self.traceback = traceback.format_exc()
                    self.error = RuntimeError(f"Error handling UDP packet: {e}")

    def run_server(self):
        try:
            host = "0.0.0.0" if self.connection.is_external else "localhost"
            port = self.connection.port  # use the connection-specific port
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind((host, port))
            self._sock.settimeout(1)  # set a timeout to allow graceful shutdown

            self.udp_handler()
        except Exception as e:
            with self.error_lock:
                self.traceback = traceback.format_exc()
                self.error = RuntimeError(f"Error creating or handling UDP server: {e}")
        finally:
            if self._sock:
                self._sock.close()

    def start_server(self):
        self.shutdown_event.clear()
        self._server_thread = threading.Thread(target=self.run_server, daemon=True)
        self._server_thread.start()
        print(f"UDP server started for connection uuid: {self.uuid}, name: {self.connection.name}")

    def stop_server(self):
        self.shutdown_event.set()
        if self._server_thread:
            self._server_thread.join()
        if self._sock:
            self._sock.close()
        print(f"UDP server stopped for connection uuid: {self.uuid}, name: {self.connection.name}")

    def is_running(self):
        return self._server_thread is not None and self._server_thread.is_alive()

    def is_shutdown(self):
        return self.shutdown_event.is_set()
