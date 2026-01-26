import os
import socket
import threading
import subprocess
import queue
import sys
import signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_PATH = os.path.join(SCRIPT_DIR, "tradewars.py")
PYTHON_EXE = sys.executable

HOST = "127.0.0.1"
PORT = 4242

class Session:
    def __init__(self, user_id):
        self.user_id = user_id
        self.proc = subprocess.Popen(
            [PYTHON_EXE, "-u", GAME_PATH, "--door"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.output_queue = queue.Queue()
        self.reader = threading.Thread(target=self._read_output, daemon=True)
        self.reader.start()

    def _read_output(self):
        for line in self.proc.stdout:
            self.output_queue.put(line)
        self.proc.stdout.close()

    def write(self, text):
        if self.proc.poll() is None:
            self.proc.stdin.write(text + "\n")
            self.proc.stdin.flush()

    def read_all(self):
        lines = []
        while not self.output_queue.empty():
            lines.append(self.output_queue.get())
        return "".join(lines)

    def close(self):
        if self.proc.poll() is None:
            try:
                self.write("0")
            except Exception:
                pass
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return self.read_all()


server_socket = None
connections = []
sessions = {}
lock = threading.Lock()


def shutdown_server(signum=None, frame=None):
    """Close all active sessions and client connections."""
    print("Shutting down TradeWars server...")
    for conn in list(connections):
        try:
            conn.sendall(b"SERVER_SHUTDOWN\n")
            conn.close()
        except Exception:
            pass
        try:
            connections.remove(conn)
        except ValueError:
            pass
    with lock:
        for sess in sessions.values():
            try:
                sess.close()
            except Exception:
                pass
        sessions.clear()
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass
    sys.exit(0)

def process_command(line):
    parts = line.strip().split(" ", 2)
    if not parts:
        return ""
    cmd = parts[0].upper()

    if cmd == "CONNECT" and len(parts) >= 2:
        user = parts[1]
        with lock:
            if user not in sessions:
                sessions[user] = Session(user)
        return sessions[user].read_all()

    if cmd == "INPUT" and len(parts) >= 3:
        user = parts[1]
        text = parts[2]
        sess = sessions.get(user)
        if not sess:
            return "ERR No session\n"
        sess.write(text)
        # allow game to generate output
        return sess.read_all()

    if cmd == "DISCONNECT" and len(parts) >= 2:
        user = parts[1]
        sess = sessions.pop(user, None)
        if sess:
            output = sess.close()
            return output + "Session closed\n"
        else:
            return "ERR No session\n"

    return "ERR Unknown command\n"


def serve():
    global server_socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        server_socket = srv
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen()
        print(f"TradeWars server listening on {HOST}:{PORT}")
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

def handle_client(conn):
    connections.append(conn)
    try:
        with conn:
            conn.sendall(b"Connected\n")
            buffer = ""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    resp = process_command(line)
                    if resp:
                        conn.sendall(resp.encode())
    finally:
        try:
            connections.remove(conn)
        except ValueError:
            pass

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown_server)
    signal.signal(signal.SIGINT, shutdown_server)
    serve()
