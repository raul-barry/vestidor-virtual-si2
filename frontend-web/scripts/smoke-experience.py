"""Opt-in browser journey against Docker: python scripts/smoke-experience.py.

Requires local Chrome, httpx and websockets; uses a temporary browser profile.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

import httpx
from websockets.sync.client import connect


def main():
    chrome = os.environ.get("CHROME_BIN", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    base = os.environ.get("VV_WEB_URL", "http://localhost:4200")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="vv-browser-") as profile:
        process = subprocess.Popen([
            chrome, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            target = None
            for _ in range(100):
                try:
                    pages = httpx.get(f"http://127.0.0.1:{port}/json", timeout=1).json()
                    target = next(p for p in pages if p["type"] == "page")
                    break
                except (httpx.HTTPError, StopIteration):
                    time.sleep(.2)
            assert target, "Chrome did not start"
            with connect(target["webSocketDebuggerUrl"], max_size=8 * 1024 * 1024) as ws:
                seq = 0
                errors = []

                def command(method, params=None):
                    nonlocal seq
                    seq += 1
                    ws.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
                    while True:
                        reply = json.loads(ws.recv(timeout=30))
                        if reply.get("method") == "Runtime.exceptionThrown":
                            errors.append(reply["params"])
                        if reply.get("id") == seq:
                            assert "error" not in reply, reply
                            return reply.get("result", {})

                def js(expression):
                    result = command("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
                    assert "exceptionDetails" not in result, result
                    return result.get("result", {}).get("value")

                def wait(expression):
                    for _ in range(150):
                        if js(expression):
                            return
                        time.sleep(.2)
                    raise AssertionError(f"Timed out: {expression}; page: {js('document.body.innerText')}")

                command("Runtime.enable")
                command("Page.enable")
                command("Page.navigate", {"url": base + "/auth/login"})
                wait("!!document.querySelector('input[type=email]')")
                js("""for (const [selector, value] of [['input[type=email]', 'cliente@vestidor.local'],
                    ['input[type=password]', 'Cliente123!']]) {
                    const input=document.querySelector(selector); input.value=value;
                    input.dispatchEvent(new Event('input', {bubbles:true}));
                } document.querySelector('button[type=submit]').click();""")
                wait("location.pathname === '/catalog' && !!document.querySelector('app-product-card')")
                wait("!!document.querySelector('app-recommendations-section article a')")
                js("document.querySelector('app-recommendations-section article a').click()")
                wait("!!document.querySelector('app-variant-selector mat-chip-option')")
                js("document.querySelector('mat-chip-listbox mat-chip-option').click()")
                js("document.querySelectorAll('mat-chip-listbox')[1].querySelector('mat-chip-option').click()")
                js("document.querySelector('a[href*=\"experience/fitting\"]').click()")
                wait("!!document.querySelector('img.garment') && document.querySelector('img.garment').naturalWidth > 0")
                assert js("location.pathname") == "/experience/fitting"
                wait("document.body.innerText.includes('Prenda lista para ajustar')")
                js("const slider=document.querySelector('input[type=range]');slider.value='125';slider.dispatchEvent(new Event('input',{bubbles:true}));")
                wait("document.querySelector('img.garment').style.left === '125px'")
                # Change product and ensure the image resource really changes.
                previous = js("document.querySelector('img.garment').src")
                js("const select=document.querySelector('select');select.selectedIndex=select.options.length-1;select.dispatchEvent(new Event('change',{bubbles:true}));")
                wait("!document.querySelector('img.garment')")
                js("Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Probar prenda')).click()")
                wait("!!document.querySelector('img.garment') && document.querySelector('img.garment').naturalWidth > 0")
                assert js("document.querySelector('img.garment').src") != previous
                command("Page.navigate", {"url": base + "/experience/recommendations"})
                wait("!!document.querySelector('article') && document.body.innerText.includes('Recomendados para ti')")
                assert not errors, errors
                print("PASS: login -> catalog -> product -> fitting image -> controls -> change garment -> recommendations")
                command("Browser.close")
            process.wait(timeout=15)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
