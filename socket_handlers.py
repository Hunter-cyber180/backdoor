import socket
from typing import Union

CHUNK_SIZE = 65536
LENGTH_BYTES = 5


def socket_send(sock: socket.socket, data: Union[str, bytes]) -> None:
    if isinstance(data, str):
        data = data.encode("utf-8")

    length = len(data)
    if length >= (1 << (8 * LENGTH_BYTES)):
        raise ValueError("Data is too large to be sent with current length prefix size")

    sock.sendall(length.to_bytes(LENGTH_BYTES, "big"))

    sent = 0
    while sent < length:
        chunk = data[sent : sent + CHUNK_SIZE]
        sock.sendall(chunk)
        sent += len(chunk)
