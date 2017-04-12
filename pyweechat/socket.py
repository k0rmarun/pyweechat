import ssl
import socket
from .exceptions import WeeChatUnknownCommandException
from .message import WeeChatMessage


class WeeChatSocket:
    def __init__(self, hostname: str = "localhost", port: int = 8000, use_ssl: bool = False):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.load_default_certs()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if use_ssl:
            self.socket = context.wrap_socket(self.socket, server_hostname=hostname)
        self.socket.connect((hostname, port))
        self.socket.setblocking(0)

        self.events = {
            "buffer_opened": None,
            "buffer_type_changed": None,
            "buffer_moved": None,
            "buffer_merged": None,
            "buffer_unmerged": None,
            "buffer_hidden": None,
            "buffer_unhidden": None,
            "buffer_remaned": None,
            "buffer_title_changed": None,
            "buffer_localvar_added": None,
            "buffer_localvar_changed": None,
            "buffer_localvar_removed": None,
            "buffer_closing": None,
            "buffer_cleared": None,
            "buffer_line_added": None,
            "nicklist": None,
            "nicklist_diff": None,
            "pong": None,
            "upgrade": None,
            "upgrade_ended": None,
        }

    def connect(self, password: str = None, compressed: bool = True) -> None:
        conection = b"init"
        if password:
            conection += b" password=" + password.encode("utf-8")
        if compressed is False:
            conection += b" compression=off"
        conection += b"\r\n"
        self.socket.sendall(conection)

    def send_async(self, data: str) -> None:
        if data:
            command = data.strip().split()[0].strip()
            if command not in ["hdata", "info", "infolist", "nicklist", "input", "sync", "desync", "quit"]:
                raise WeeChatUnknownCommandException(command)
            self.socket.sendall(data.encode() + b"\r\n")

    def poll(self) -> WeeChatMessage:
        try:
            response = self.socket.recv(4096 * 1024)
        except socket.error:
            return None

        if response:
            response = WeeChatMessage(response)
            if response.id:
                id = response.id
                if id[0] == "_":
                    id = id[1:]
                if id in self.events.keys() and self.events[id] is not None:
                    self.events[id](response.get_hdata_result())
            return response
        return None

    def on(self, event: str, callback: callable = None) -> None:
        if event in self.events.keys():
            self.events[event] = callback

    def disconnect(self) -> None:
        self.socket.sendall(b"quit\r\n")
        self.socket.close()

    def wait(self) -> WeeChatMessage:
        while True:
            ret = self.poll()
            if ret is not None:
                return ret

    def send(self, data: str) -> WeeChatMessage:
        self.send_async(data)
        return self.wait()
