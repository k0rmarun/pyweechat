from .socket import WeeChatSocket
from .buffer import WeeChatBuffer
from datetime import datetime, timedelta
from pprint import pprint


class WeeChatClient:
    def __init__(self, **kwargs):
        self.socket = WeeChatSocket(kwargs.get("hostname", "localhost"), kwargs.get("port", 8000),
                                    kwargs.get("use_ssl", False))
        self.socket.connect(kwargs.get("password"), kwargs.get("compressed", True))

        self.buffers = []
        self.setup()

    def get_buffer_by_pointer(self, pointer: str) -> WeeChatBuffer:
        if pointer is None:
            return None
        for buffer in self.buffers:
            if buffer.pointer == pointer:
                return buffer
        return None

    def get_buffer_by_number(self, number: int) -> WeeChatBuffer:
        if number is None:
            return None
        for buffer in self.buffers:
            if buffer.number == number:
                return buffer
        return None

    def get_buffer_by_name(self, name: str) -> WeeChatBuffer:
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

    def setup(self):
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

        self.sync("*")

    def on_buffer_opened(self, response: dict):
        self.buffers.append(WeeChatBuffer(response))

    def on_buffer_moved(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if buffer:
            buffer.number = message.get("number", -1)

    def on_buffer_line_added(self, message: dict):
        buffer = self.get_buffer_by_pointer(message.get("pointer"))
        if buffer:
            buffer.add_line(message)

    def on_buffer_cleared(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.lines.clear()

    def on_buffer_renamed(self, message: dict):
        buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.full_name = message.get("full_name")
            buffer.short_name = message.get("short_name")

    def on_buffer_title_changed(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            buffer.title = message.get("title")

    def on_buffer_closing(self, message: dict):
        buffer = self.get_buffer_by_name(message.get("full_name"))
        if not buffer:
            buffer = self.get_buffer_by_number(message.get("number"))
        if buffer:
            self.buffers.remove(buffer)

    def on_nicklist(self, message: dict):
        buffer = self.get_buffer_by_pointer(message.get("__path")[0])
        if buffer:
            buffer.nicklist = []
            for nick in message:
                buffer.add_nick(nick)

    def on_nicklist_diff(self, message: dict):
        pass

    def sync(self, channel: str):
        self.socket.send_async("sync " + channel)

    def desync(self, channel: str):
        self.socket.send_async("desync " + channel)

    def input(self, buffer: str, message: str) -> dict:
        return self.socket.send("input {} {}".format(buffer, message)).get_hdata_result()

    def run(self, periodic_callback=None, delta: timedelta = None):
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
