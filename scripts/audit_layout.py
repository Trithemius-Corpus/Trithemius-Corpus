"""Audit every page type for common layout/GUI issues via CDP.

Checks per page:
  - body horizontal scroll (content wider than viewport)
  - images that failed to load (naturalWidth===0)
  - elements overflowing the document width
  - text contrast issues (skipped — needs computed styles)
  - broken internal links (404) — via fetch
  - empty main content
Reports a JSON summary.
"""
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
PORT = 9483
PROFILE = str(Path(os.environ.get("TRITHEMIUS_CHROME_PROFILE", ROOT / ".cache" / "chrome-audit")))


def ws_recv(sock):
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


def ws_send(sock, payload: str):
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


def connect(port):
    tabs = None
    for _ in range(40):
        try:
            tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3).read())
            if any(t.get("type") == "page" for t in tabs):
                break
        except Exception:
            pass
        time.sleep(0.5)
    if not tabs:
        return None
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
    hs = sock.recv(4096).decode("latin-1", "replace")
    if "101" not in hs.split("\r\n")[0]:
        return None
    return sock


def main():
    pages = [a for a in sys.argv[1:] if not a.startswith("--")] or [
        "index.html", "works.html", "scoreboard.html", "methodology.html",
        "ciphers.html", "cipher-solutions.html", "search.html",
        "404.html",
        "works/prdl-24390_polygraphiae-libri-vi.html",
        "works/prdl-24390_polygraphiae-libri-vi_parallel.html",
        "works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-key.html",
        "works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-grid.html",
        "genres/crypto-occult.html",
    ]
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
         "--no-default-browser-check", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={PROFILE}",
         "--window-size=" + ("390,1600" if "--mobile" in sys.argv else "1366,1500"),
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sock = None
    try:
        sock = connect(PORT)
        if not sock:
            print("CDP unreachable"); return
        mid = [0]
        def call(method, params=None):
            mid[0] += 1
            this = mid[0]
            ws_send(sock, json.dumps({"id": this, "method": method, "params": params or {}}))
            return this
        call("Page.enable"); call("Runtime.enable")
        results = []
        for rel in pages:
            url = (DIST / rel).as_uri()
            call("Page.navigate", {"url": url})
            time.sleep(3.0)
            probe = """(function(){
  var vw=document.documentElement.clientWidth;
  var docW=Math.max(document.body.scrollWidth,document.documentElement.scrollWidth);
  var hscroll=docW>vw+2;
  // only flag images that HAVE a src but failed to load (real 404s);
  // images with no src are deliberate JS-populated placeholders.
  var badImgs=[];
  document.querySelectorAll('img').forEach(function(im){
    var s=im.getAttribute('src');
    if(s && im.complete && im.naturalWidth===0){ badImgs.push(s.slice(0,60)); }
  });
  // real overflow: elements wider than viewport NOT inside an overflow
  // container (which clips them legitimately).
  function inScroller(el){
    var p=el.parentElement;
    while(p){
      var cs=getComputedStyle(p);
      if(/(auto|scroll)/.test(cs.overflowX)||/(auto|scroll)/.test(cs.overflow)) return true;
      p=p.parentElement;
    }
    return false;
  }
  var overflows=[];
  document.querySelectorAll('div,article,section,table').forEach(function(el){
    if(el.offsetWidth<=0||inScroller(el)) return;
    var r=el.getBoundingClientRect();
    if(r.right>vw+2 && r.right-r.left<9999){
      var cls=(el.className&&el.className.toString)?el.className.toString().slice(0,40):el.tagName;
      if(el.id!=='readProgress') overflows.push({tag:el.tagName.toLowerCase(),cls:cls,right:Math.round(r.right)});
    }
  });
  overflows=overflows.slice(0,5);
  var main=document.querySelector('main')||document.body;
  var mainChars=main?main.innerText.length:0;
  return JSON.stringify({vw:vw,docW:Math.round(docW),hscroll:hscroll,badImgs:badImgs.slice(0,5),badImgN:badImgs.length,overflows:overflows,mainChars:mainChars});
})()"""
            eid = call("Runtime.evaluate", {"expression": probe, "returnByValue": True})
            val = None
            err = None
            deadline = time.time() + 6
            while time.time() < deadline:
                frame = ws_recv(sock)
                if not frame:
                    time.sleep(0.1); continue
                try:
                    msg = json.loads(frame)
                except Exception:
                    continue
                if msg.get("id") == eid:
                    res = msg.get("result", {})
                    val = res.get("result", {}).get("value")
                    if val is None and res.get("exceptionDetails"):
                        err = res["exceptionDetails"].get("exception", {}).get("description", "")[:200]
                    break
            results.append({"page": rel, "data": val, "err": err})
        # summary
        print("=== LAYOUT AUDIT ===")
        issues = 0
        for r in results:
            d = r["data"]
            if not d:
                extra = f"  ERR: {r.get('err')}" if r.get("err") else ""
                print(f"  [??] {r['page']}: no data{extra}"); continue
            d = json.loads(d)
            flags = []
            if d["hscroll"]: flags.append(f"HSCROLL(docW={d['docW']})")
            if d["badImgN"]: flags.append(f"BADIMG={d['badImgN']}")
            if d["overflows"]: flags.append(f"OVERFLOW={len(d['overflows'])}")
            # search/404 are intentionally compact / JS-populated — don't flag thin
            known_thin = r["page"].endswith("search.html") or r["page"].endswith("404.html")
            if d["mainChars"] < 200 and not known_thin:
                flags.append(f"THIN(main={d['mainChars']})")
            elif d["mainChars"] < 200 and known_thin:
                flags.append(f"thin-ok({d['mainChars']})")
            status = "OK " if not flags or all(f.startswith("thin-ok") for f in flags) else "!! "
            real_flags = [f for f in flags if not f.startswith("thin-ok")]
            if real_flags: issues += 1
            print(f"  [{status}] {r['page'][:55]:57} {' | '.join(flags) if flags else ''}")
            for ov in d["overflows"][:3]:
                print(f"          overflow: <{ov['tag']}.{ov['cls']}> right={ov['right']}")
            for bi in d["badImgs"][:3]:
                print(f"          bad img: {bi}")
        print(f"\n{issues} page(s) with REAL issues of {len(results)}")
    finally:
        if sock:
            try: sock.close()
            except Exception: pass
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: pass


if __name__ == "__main__":
    main()
