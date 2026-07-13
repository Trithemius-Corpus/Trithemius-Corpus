"""Measure rendered table geometry via Chrome CDP (self-contained)."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ROOT = Path(__file__).resolve().parents[1]
DIST = (ROOT / "site" / "dist").resolve()
PORT = 9417
PROFILE = str(Path(os.environ.get("TRITHEMIUS_CHROME_PROFILE", ROOT / ".cache" / "chrome-measure")))


def ws_frame_recv(sock):
    hdr = sock.recv(2)
    if len(hdr) < 2:
        return None
    b2 = hdr[1]
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F
    if length == 126:
        length = int.from_bytes(sock.recv(2), "big")
    elif length == 127:
        length = int.from_bytes(sock.recv(8), "big")
    mask = sock.recv(4) if masked else b""
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    if masked:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return data


def ws_frame_send(sock, payload: str):
    data = payload.encode("utf-8")
    length = len(data)
    hdr = bytearray([0x81])
    if length < 126:
        hdr.append(0x80 | length)
    elif length < 65536:
        hdr.append(0x80 | 126); hdr += length.to_bytes(2, "big")
    else:
        hdr.append(0x80 | 127); hdr += length.to_bytes(8, "big")
    mask = b"\x01\x02\x03\x04"
    sock.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def main():
    rel = sys.argv[1] if len(sys.argv) > 1 else "works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-key.html"
    url = (DIST / rel).as_uri()
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
         "--no-default-browser-check", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={PROFILE}", "--window-size=1366,2000", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sock = None
    try:
        tabs = None
        for _ in range(40):
            try:
                tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3).read())
                if any(t.get("type") == "page" for t in tabs):
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not tabs:
            print("CDP unreachable"); return
        tab = next(t for t in tabs if t.get("type") == "page")
        ws_url = tab["webSocketDebuggerUrl"]
        host = ws_url.split("//")[1].split("/")[0].split(":")[0]
        port = int(ws_url.split("//")[1].split("/")[0].split(":")[1])
        path = "/" + ws_url.split("/", 3)[3]
        sock = socket.create_connection((host, port), timeout=10)
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
                      f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                      f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        handshake = sock.recv(4096).decode("latin-1", "replace")
        if "101" not in handshake.split("\r\n")[0]:
            print("WS upgrade failed:", handshake[:150]); return
        mid = [0]
        def call(method, params=None):
            mid[0] += 1
            this = mid[0]
            ws_frame_send(sock, json.dumps({"id": this, "method": method, "params": params or {}}))
            return this
        call("Page.enable"); call("Runtime.enable")
        call("Page.navigate", {"url": url})
        time.sleep(6.0)
        probe = (
            "(function(){"
            "var wide=document.querySelectorAll('.style-c-pair[data-wide]').length;"
            "var col=document.querySelector('.style-c-rendering');"
            "var colW=col?Math.round(col.getBoundingClientRect().width):-1;"
            "var pair=document.querySelector('.style-c-pair');"
            "var pairW=pair?Math.round(pair.getBoundingClientRect().width):-1;"
            "var ts=document.querySelectorAll('.table-scroll');"
            "var out=[];"
            "ts.forEach(function(t,i){"
            "if(i>4)return;"
            "var tbl=t.querySelector('table');"
            "var tw=tbl?Math.round(tbl.scrollWidth):-1;"
            "var ow=tbl?Math.round(tbl.offsetWidth):-1;"
            "var cw=Math.round(t.clientWidth);"
            "var pp=t.closest('.style-c-pair');"
            "var facs=pp?pp.querySelector('.style-c-facsimile'):null;"
            "var r=pp?pp.querySelector('.style-c-rendering'):null;"
            "out.push({i:i,tblScrollW:tw,tblOffsetW:ow,scrollClientW:cw,renderW:r?Math.round(r.clientWidth):-1,overflows:tw>cw,isWide:pp?pp.hasAttribute('data-wide'):false,facsW:facs?Math.round(facs.getBoundingClientRect().width):0,cols:tbl?tbl.querySelectorAll('th').length:0});"
            "});"
            "return JSON.stringify({pairW:pairW,colW:colW,wideChunks:wide,scrollers:ts.length,samples:out});"
            "})()"
        )
        eid = call("Runtime.evaluate", {"expression": probe, "returnByValue": True})
        result = None
        deadline = time.time() + 8
        while time.time() < deadline:
            frame = ws_frame_recv(sock)
            if not frame:
                time.sleep(0.15); continue
            try:
                msg = json.loads(frame)
            except Exception:
                continue
            if msg.get("id") == eid:
                result = msg.get("result", {}).get("result", {}).get("value")
                break
        print(f"PAGE: {rel}")
        print(f"PROBE: {result}")
    finally:
        if sock:
            try: sock.close()
            except Exception: pass
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: pass


if __name__ == "__main__":
    main()
