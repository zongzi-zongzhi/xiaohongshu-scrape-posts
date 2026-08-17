from __future__ import annotations

import argparse
import select
import socket
import socketserver
import sys
from typing import Tuple
from urllib.parse import urlsplit


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ConnectProxyHandler(socketserver.BaseRequestHandler):
    bind_ip: str = ""

    def handle(self) -> None:
        self.request.settimeout(20)
        try:
            header = self._read_header()
            if not header:
                return
            first = header.split(b"\r\n", 1)[0].decode("iso-8859-1", "replace")
            method, target, _ = first.split(" ", 2)
            if method.upper() != "CONNECT":
                self._forward_http(method, target, header)
                return
            host, port = self._parse_target(target)
            upstream = socket.create_connection((host, port), timeout=20, source_address=(self.bind_ip, 0))
            upstream.settimeout(None)
            self.request.settimeout(None)
            self.request.sendall(b"HTTP/1.1 200 Connection Established\r\nProxy-Agent: bound-connect\r\n\r\n")
            self._relay(self.request, upstream)
        except Exception as exc:
            try:
                self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except Exception:
                pass
            print(f"proxy error: {exc}", file=sys.stderr, flush=True)

    def _read_header(self) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while total < 65536:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            data = b"".join(chunks)
            if b"\r\n\r\n" in data:
                return data.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"
        return b""

    @staticmethod
    def _parse_target(target: str) -> Tuple[str, int]:
        if ":" not in target:
            return target, 443
        host, port = target.rsplit(":", 1)
        return host.strip("[]"), int(port)

    def _forward_http(self, method: str, target: str, header: bytes) -> None:
        lines = header.split(b"\r\n")
        version = b"HTTP/1.1"
        parsed = urlsplit(target)
        if parsed.scheme and parsed.hostname:
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
        else:
            host_value = ""
            for line in lines[1:]:
                if line.lower().startswith(b"host:"):
                    host_value = line.split(b":", 1)[1].strip().decode("iso-8859-1")
                    break
            if not host_value:
                self.request.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
                return
            if ":" in host_value:
                host, port_text = host_value.rsplit(":", 1)
                port = int(port_text)
            else:
                host, port = host_value, 80
            path = target

        upstream = socket.create_connection((host, port), timeout=20, source_address=(self.bind_ip, 0))
        upstream.settimeout(None)
        self.request.settimeout(None)

        filtered = []
        for line in lines[1:]:
            low = line.lower()
            if low.startswith(b"proxy-connection:"):
                continue
            if low.startswith(b"connection:"):
                continue
            filtered.append(line)
        request = b" ".join([method.encode("ascii", "replace"), path.encode("iso-8859-1", "replace"), version])
        upstream.sendall(request + b"\r\n" + b"\r\n".join(filtered) + b"\r\n")
        self._relay(self.request, upstream)

    @staticmethod
    def _relay(left: socket.socket, right: socket.socket) -> None:
        sockets = [left, right]
        try:
            while True:
                readable, _, exceptional = select.select(sockets, [], sockets, 60)
                if exceptional:
                    break
                if not readable:
                    break
                for src in readable:
                    dst = right if src is left else left
                    data = src.recv(65536)
                    if not data:
                        return
                    dst.sendall(data)
        finally:
            for sock in sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-ip", required=True)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=18088)
    args = parser.parse_args()

    ConnectProxyHandler.bind_ip = args.bind_ip
    with ThreadingTCPServer((args.listen_host, args.listen_port), ConnectProxyHandler) as server:
        print(f"listening {args.listen_host}:{args.listen_port} bound={args.bind_ip}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
