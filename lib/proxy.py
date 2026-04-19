# -*- coding: utf-8 -*-

import socket
import threading
import requests
from urllib.parse import quote, unquote, urljoin
import time
import os
import signal
import re


def kill_process_on_port(port):
    try:
        import subprocess
        commands = [
            f"lsof -ti:{port}",
            f"ss -lptn 'sport = :{port}' | grep -oP 'pid=\\K[0-9]+'",
            f"netstat -nlp | grep :{port} | awk '{{print $7}}' | cut -d'/' -f1",
        ]
        
        pid = None
        for cmd in commands:
            try:
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
                pid = result.decode().strip()
                if pid and pid.isdigit():
                    break
            except Exception:
                continue
        
        if pid and pid.isdigit():
            pid = int(pid)
            if pid != os.getpid():
                try:
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.3)
                    return True
                except (ProcessLookupError, PermissionError):
                    return False
        return False
    except Exception:
        return False


def is_port_in_use(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.close()
        return False
    except OSError:
        return True


def is_port_responding(port, timeout=0.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


class StreamProxy:
    def __init__(self, port=8899):
        self.port = port
        self.server = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return True

        if is_port_in_use(self.port):
            if is_port_responding(self.port, timeout=0.3):
                self.running = True
                return True
            
            if kill_process_on_port(self.port):
                time.sleep(0.5)
            
            if is_port_in_use(self.port):
                if is_port_responding(self.port, timeout=0.3):
                    self.running = True
                    return True

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass
            
            self.server.bind(("127.0.0.1", self.port))
            self.server.listen(5)
            self.server.settimeout(1.0)
        except OSError as e:
            if "Address already in use" in str(e):
                if is_port_responding(self.port, timeout=0.5):
                    self.running = True
                    return True
            return False
        except Exception:
            return False

        self.running = True
        self.thread = threading.Thread(target=self._accept)
        self.thread.daemon = True
        self.thread.start()
        return True

    def _accept(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                t = threading.Thread(target=self._handle, args=(client,))
                t.daemon = True
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle(self, client):
        try:
            raw = client.recv(8192)
            if not raw:
                return

            req = raw.decode("utf-8", errors="ignore")
            lines = req.splitlines()
            if not lines:
                return
                
            line = lines[0]
            parts = line.split()
            if len(parts) < 2:
                return

            path = parts[1]
            if "/proxy?url=" not in path:
                self._send_error(client, 400)
                return

            range_header = None
            for req_line in lines[1:]:
                if req_line.lower().startswith("range:"):
                    range_header = req_line.split(":", 1)[1].strip()
                    break

            encoded = path.split("/proxy?url=", 1)[1]
            encoded = encoded.split(" HTTP/")[0]
            decoded = unquote(encoded)
            url, headers = self._parse_url_headers(decoded)
            self._process_request(client, url, headers, range_header)

        except Exception:
            pass
        finally:
            try:
                client.close()
            except:
                pass

    def _parse_url_headers(self, value):
        headers = {}
        if "|" in value:
            url, h = value.split("|", 1)
            for p in h.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    headers[k] = unquote(v.replace("+", " "))
            return url, headers
        return value, headers

    def _is_valid_mp4_start(self, data):
        if len(data) < 8:
            return False
        
        valid_atoms = [b'ftyp', b'moov', b'mdat', b'free', b'skip', b'wide', b'pnot']
        
        atom_type = data[4:8]
        if atom_type in valid_atoms:
            return True
        
        for i in range(min(20, len(data) - 8)):
            atom_type = data[i+4:i+8]
            if atom_type in valid_atoms:
                return i < 8
        
        return False

    def _has_garbage_prefix(self, data):
        garbage_signatures = [
            b"\x89PNG\r\n\x1a\n",
            b"GIF8",
            b"\xff\xd8\xff",
            b"RIFF"
        ]
        
        for sig in garbage_signatures:
            if data.startswith(sig):
                return True
        
        return False

    def _process_request(self, client, url, headers, range_header=None):
        try:
            request_headers = {
                "User-Agent": headers.get("User-Agent", "Mozilla/5.0"),
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Referer": headers.get("Referer", ""),
                "Origin": headers.get("Origin", ""),
            }
            
            if range_header:
                request_headers["Range"] = range_header
            
            r = requests.get(
                url,
                headers=request_headers,
                stream=True,
                allow_redirects=True,
                timeout=20
            )
        except Exception:
            self._send_error(client, 500)
            return

        content_type = r.headers.get("Content-Type", "").lower()
        is_m3u8_by_content_type = "m3u8" in content_type or "mpegurl" in content_type
        is_m3u8_by_url = url.lower().endswith(".m3u8") or "cdn_stream.m3u8" in url.lower()
        
        first_chunk = next(r.iter_content(1024), b"")
        is_m3u8_by_content = first_chunk.startswith(b"#EXTM3U")
        is_playlist = is_m3u8_by_content_type or is_m3u8_by_url or is_m3u8_by_content

        if is_playlist:
            try:
                remaining_chunks = []
                for chunk in r.iter_content(8192):
                    if chunk:
                        remaining_chunks.append(chunk)
                remaining = b"".join(remaining_chunks).decode("utf-8")
                text = first_chunk.decode("utf-8") + remaining
            except Exception:
                self._send_error(client, 500)
                return
            
            base = url.rsplit("/", 1)[0] + "/"
            rewritten = self._rewrite_m3u8(text, base, headers)

            try:
                client.send(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/vnd.apple.mpegurl\r\n"
                    b"Connection: close\r\n\r\n"
                )
                client.send(rewritten.encode("utf-8"))
            except Exception:
                pass
            return

        is_clean = self._is_valid_mp4_start(first_chunk)
        has_garbage = self._has_garbage_prefix(first_chunk)
        
        if has_garbage:
            self._stream_with_cleaning(client, r, first_chunk)
        elif range_header or is_clean:
            self._stream_direct(client, r, first_chunk, range_header)
        else:
            self._stream_with_cleaning(client, r, first_chunk)

    def _stream_direct(self, client, response, first_chunk, range_header):
        try:
            status_code = response.status_code
            
            if status_code == 206:
                headers = b"HTTP/1.1 206 Partial Content\r\n"
                
                if "Content-Range" in response.headers:
                    headers += f"Content-Range: {response.headers['Content-Range']}\r\n".encode()
                
                if "Content-Length" in response.headers:
                    headers += f"Content-Length: {response.headers['Content-Length']}\r\n".encode()
            else:
                headers = b"HTTP/1.1 200 OK\r\n"
                
                if "Content-Length" in response.headers:
                    headers += f"Content-Length: {response.headers['Content-Length']}\r\n".encode()
            
            if "Content-Type" in response.headers:
                headers += f"Content-Type: {response.headers['Content-Type']}\r\n".encode()
            else:
                headers += b"Content-Type: video/mp4\r\n"
            
            headers += b"Accept-Ranges: bytes\r\n"
            headers += b"Connection: close\r\n\r\n"
            
            client.send(headers)
        except Exception:
            return

        try:
            client.send(first_chunk)
            
            for chunk in response.iter_content(16384):
                if not chunk:
                    continue
                client.send(chunk)
        except Exception:
            pass

    def _stream_with_cleaning(self, client, response, first_chunk):
        try:
            client.send(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: video/mp4\r\n"
                b"Connection: close\r\n"
                b"Accept-Ranges: none\r\n\r\n"
            )
        except Exception:
            return

        buffer = first_chunk
        sent = False

        for sig in (b"\x89PNG\r\n\x1a\n", b"GIF8", b"\xff\xd8\xff", b"RIFF"):
            if buffer.startswith(sig):
                buffer = buffer[len(sig):]

        idx = buffer.find(b"ftyp")
        if idx != -1:
            start = max(0, idx - 4)
            try:
                client.send(buffer[start:])
                sent = True
                buffer = b""
            except Exception:
                return
        elif len(buffer) > 1024:
            try:
                client.send(buffer)
                sent = True
                buffer = b""
            except Exception:
                return

        for chunk in response.iter_content(16384):
            if not chunk:
                continue
            try:
                if not sent:
                    buffer += chunk
                    for sig in (b"\x89PNG\r\n\x1a\n", b"GIF8", b"\xff\xd8\xff", b"RIFF"):
                        if buffer.startswith(sig):
                            buffer = buffer[len(sig):]
                    idx = buffer.find(b"ftyp")
                    if idx != -1:
                        start = max(0, idx - 4)
                        client.send(buffer[start:])
                        sent = True
                        buffer = b""
                    elif len(buffer) > 65536:
                        client.send(buffer)
                        sent = True
                        buffer = b""
                else:
                    client.send(chunk)
            except Exception:
                break

    def _rewrite_m3u8(self, content, base, headers):
        out = []
        
        for line in content.splitlines():
            l = line.strip()
            
            if not l:
                out.append(l)
                continue
            
            if l.startswith("#") and "URI=" not in l:
                out.append(l)
                continue
            
            if l.startswith("#") and "URI=" in l:
                def rewrite_uri(match):
                    uri = match.group(1)
                    
                    if not uri.startswith("http"):
                        uri = urljoin(base, uri)
                    
                    if headers:
                        h = "&".join(f"{k}={quote(v)}" for k, v in headers.items())
                        uri = f"{uri}|{h}"
                    
                    proxied = self.get_proxy_url(uri)
                    return f'URI="{proxied}"'
                
                rewritten_line = re.sub(r'URI=["\'](.*?)["\']', rewrite_uri, l)
                out.append(rewritten_line)
                continue
            
            if not l.startswith("http"):
                l = urljoin(base, l)
            
            if headers:
                h = "&".join(f"{k}={quote(v)}" for k, v in headers.items())
                l = f"{l}|{h}"
            
            l = self.get_proxy_url(l)
            out.append(l)
        
        return "\n".join(out)

    def get_proxy_url(self, url):
        return f"http://127.0.0.1:{self.port}/proxy?url={quote(url, safe='')}"

    def _send_error(self, client, code):
        try:
            client.send(f"HTTP/1.1 {code} Error\r\n\r\n".encode())
        except Exception:
            pass

    def stop(self):
        self.running = False
        try:
            self.server.close()
        except Exception:
            pass


_proxy = None

def get_proxy():
    global _proxy
    
    if _proxy is None:
        _proxy = StreamProxy()
        if not _proxy.start():
            return None
    else:
        if not is_port_responding(8899, timeout=0.3):
            try:
                _proxy.stop()
            except Exception:
                pass
            _proxy = StreamProxy()
            if not _proxy.start():
                return None
    
    return _proxy
