from socket_handlers import *
import os


def pwd(socket):
    socket_send(socket, os.getcwd().encode("utf-8"))
