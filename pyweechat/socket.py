import ssl
import socket
from .exceptions import WeeChatUnknownCommandException
from .message import WeeChatMessage
import sys


def create_ssl_context(protocol_version=None):
    if protocol_version is not None:
        return ssl.SSLContext(protocol_version)

    if sys.version_info >= (3, 6):  # Auto select best available version only available in python 3.6+
        return ssl.SSLContext(ssl.PROTOCOL_TLS)
    return ssl.SSLContext(ssl.PROTOCOL_TLSv1)


class WeeChatSocket:
    """
    Socket to interact with the weechat relay server.
    """

    def __init__(self, hostname: str = "localhost", port: int = 8000, use_ssl: bool = False, custom_cert: dict = None,
                 custom_ssl_protocol=None):
        """
        Setup socket which is used to connect to the Weechat relay
        :param hostname: hostname or ip address of the desired weechat relay server
        :param port: port on which the weechat relay server ist listening
        :param use_ssl: secure the transmission via SSL/TLS.
        :param custom_cert: enforce a specific certificate (might be self signed). See SSLContext.load_verify_locations for specific parameter names
        :param custom_ssl_protocol: custom ssl.PROTOCOL enum to use. If not set WeeChatSocket will select the best available version (if python 3.6+) or fall back to TLSv1
        """

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if use_ssl:
            context = create_ssl_context(custom_ssl_protocol)
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True
            if custom_cert:
                context.load_verify_locations(**custom_cert)
            else:
                context.load_default_certs()

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
        """
        Initialize the connection with the weechat relay
        :param password: Password to use. None if unauthenticated
        :param compressed: Request response to be compressed
        """
        conection = b"init"
        if password:
            conection += b" password=" + password.encode("utf-8")
        if compressed is False:
            conection += b" compression=off"
        conection += b"\r\n"
        self.socket.sendall(conection)

    def send_async(self, data: str) -> None:
        """
        Send data to the weechat relay. Do not await response
        :param data: Data to send. First word must be a valid weechat relay command
        """
        if data:
            command = data.strip().split()[0].strip()
            if command not in ["ping", "hdata", "info", "infolist", "nicklist", "input", "sync", "desync", "quit"]:
                raise WeeChatUnknownCommandException(command)
            self.socket.sendall(data.encode() + b"\r\n")

    def poll(self) -> WeeChatMessage:
        """
        Poll for new data from weechat relay server. Trigger registered events
        Must be called within the relay servers socket timeout period
        :return: WeeChatMessage or None if error or nothing new
        """
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
        """
        Register event callback
        :param event: name of the subscribed event
        :param callback: function to call. None to end listening
        """
        if event in self.events.keys():
            self.events[event] = callback

    def disconnect(self) -> None:
        """
        Gracefully end connection with weechat relay
        """
        self.socket.sendall(b"quit\r\n")
        self.socket.close()

    def wait(self) -> WeeChatMessage:
        """
        Waits for a response from relay server. Does not block interpreter thread, but has higher processor usage
        :return: WeeChatMessage
        """
        while True:
            ret = self.poll()
            if ret is not None:
                return ret

    def send(self, data: str) -> WeeChatMessage:
        """
        Send data to the weechat relay, wait for response
        :param data: data to send to the relay. First word must be a valid weechat relay command
        :return: WeeChatMessage
        """
        self.send_async(data)
        return self.wait()
