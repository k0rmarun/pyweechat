from .socket import WeeChatSocket
from .buffer import WeeChatBuffer
from datetime import datetime, timedelta
from pprint import pprint


class WeeChatClient:
    """
    Hight level interaction with weechat server
    """
    def __init__(self, **kwargs):
        """
        Connect to weechat relay server and requests information for available buffers
        :param hostname
        :param port
        :param use_ssl
        :param custom_cert
        :param password
        :param compressed
        """
        self.socket = WeeChatSocket(kwargs.get("hostname", "localhost"), kwargs.get("port", 8000),
                                    kwargs.get("use_ssl", False), kwargs.get("custom_cert", None))
        self.socket.connect(kwargs.get("password"), kwargs.get("compressed", True))

        self.buffers = []
        self._setup()

    def get_buffer_by_pointer(self, pointer: str) -> WeeChatBuffer:
        """
        Search for a buffer with a given pointer
        :param pointer: Pointer to search for
        :return: WeeChatBuffer or None if no such buffer
        """
        if pointer is None:
            return None
        for buffer in self.buffers:
            if buffer.pointer == pointer:
                return buffer
        return None

    def get_buffer_by_number(self, number: int) -> WeeChatBuffer:
        """
        Search for a buffer with a given index
        :param number: index to search for
        :return: WeeChatBuffer or None if no such buffer
        """
        if number is None:
            return None
        for buffer in self.buffers:
            if buffer.number == number:
                return buffer
        return None

    def get_buffer_by_name(self, name: str) -> WeeChatBuffer:
        """
        Search for a buffer with a given name.
        Searches for either the full name, short name or title
        :param name: name to search for
        :return: WeeChatBuffer or None if no such buffer
        """
        if name is None:
            return None
        for buffer in self.buffers:
            if buffer.full_name == name:
                return buffer
            if buffer.name == name:
                return buffer
            if buffer.short_name == name:
                return buffer
        return None

    def _setup(self):
        """
        Requests data from all buffers
        :return:
        """

        last = "gui_buffers"
        while True:
            buf, raw = WeeChatBuffer.from_pointer(self.socket, last)

            if buf:
                self.buffers.append(buf)
            if raw:
                if raw.get("next_buffer") is not None and raw.get("next_buffer") != "0":
                    last = raw.get("next_buffer")
                else:
                    break

        # Setup event handling only after reading buffers completed
        self.socket.on("buffer_opened", self._on_buffer_opened)
        self.socket.on("buffer_type_changed", None) # NIY
        self.socket.on("buffer_moved", self._on_buffer_moved)
        self.socket.on("buffer_merged", None) # NIY
        self.socket.on("buffer_unmerged", None) # NIY
        self.socket.on("buffer_hidden", None) # NIY
        self.socket.on("buffer_unhidden", None) # NIY
        self.socket.on("buffer_remaned", self._on_buffer_renamed)
        self.socket.on("buffer_title_changed", self._on_buffer_title_changed)
        self.socket.on("buffer_localvar_added", None) # NIY
        self.socket.on("buffer_localvar_changed", None) # NIY
        self.socket.on("buffer_localvar_removed", None) # NIY
        self.socket.on("buffer_closing", self._on_buffer_closing)
        self.socket.on("buffer_cleared", self._on_buffer_cleared)
        self.socket.on("nicklist", self._on_nicklist)
        self.socket.on("nicklist_diff", self._on_nicklist_diff) # NIY
        self.socket.on("pong", None) # NIY
        self.socket.on("upgrade", None) # NIY
        self.socket.on("upgrade_ended", None) # NIY

        self.sync("*")

    def _on_buffer_opened(self, response: dict):
        self.buffers.append(WeeChatBuffer(response))

    def _on_buffer_moved(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if buffer:
            buffer.number = message.get("number", -1)

    def _on_buffer_line_added(self, message: dict):
        buffer = self.get_buffer_by_pointer(message.get("pointer"))
        if buffer:
            buffer.add_line(message)

    def _on_buffer_cleared(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.lines.clear()

    def _on_buffer_renamed(self, message: dict):
        buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.full_name = message.get("full_name")
            buffer.short_name = message.get("short_name")

    def _on_buffer_title_changed(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.title = message.get("title")

    def _on_buffer_closing(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            self.buffers.remove(buffer)

    def _on_nicklist(self, message: dict):
        buffer = self.get_buffer_by_pointer(message.get("__path")[0])
        if buffer:
            buffer.nicklist = []
            for nick in message:
                buffer.add_nick(nick)

    def _on_nicklist_diff(self, message: dict):
        pass

    def sync(self, channel: str):
        """
        Request updates on buffer
        :param channel: Buffer to get updates for
        :return:
        """
        self.socket.send_async("sync " + channel)

    def desync(self, channel: str):
        """
        Request to nolonger receive updates for a buffer
        :param channel: Buffer to get updates for
        :return:
        """
        self.socket.send_async("desync " + channel)

    def input(self, buffer: str, message: str) -> dict:
        """
        Send a messag to the server
        :param buffer: buffer name to send the message from
        :param message: message to send
        :return: Response
        """
        return self.socket.send("input {} {}".format(buffer, message)).get_hdata_result()

    def run(self, periodic_callback=None, delta: timedelta = None):
        """
        Start main loop. Executes a periodic callback
        :param periodic_callback: function to call periodically. Return false to stop main loop
        :param delta: Call callback ever delta seconds
        :return:
        """
        now = datetime.now()
        while True:
            if periodic_callback and delta:
                if now + delta < datetime.now():
                    now = datetime.now()
                    if not periodic_callback():
                        break
            self.socket.poll()

    def print(self):
        for buffer in self.buffers:
            pprint(vars(buffer), width=300, indent=4)
