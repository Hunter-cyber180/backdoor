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


def socket_recv(sock: socket.socket, decode_as_utf8: bool = True) -> Union[bytes, str]:

    length_data = b""
    while len(length_data) < 5:
        chunk = sock.recv(5 - len(length_data))
        if not chunk:
            raise ConnectionError("Connection closed while receiving length prefix")
        length_data += chunk

    length = int.from_bytes(length_data, "big")

    received_data = b""
    while len(received_data) < length:
        remaining_bytes = length - len(received_data)
        chunk = sock.recv(1024 if remaining_bytes > 1024 else remaining_bytes)
        if not chunk:
            raise ConnectionError("Connection closed before receiving all data")
        received_data += chunk

    return received_data.decode("utf-8") if decode_as_utf8 else received_data
