# мини-прокладка cobalt -> bgutil: cobalt шлёт POST /get_pot без заголовков,
# bgutil требует Content-Type: application/json; добавляем и прокидываем ответ
import json, os, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

BG = os.environ.get("BG_URL", "http://bgpot:4416")


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/get_pot":
            self.send_error(404); return
        req = urllib.request.Request(BG + "/get_pot", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(502); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body); return
        import time
        data.setdefault("updated", int(time.time() * 1000))
        body = json.dumps(data).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):  # тише в логах
        pass


HTTPServer(("0.0.0.0", 8080), H).serve_forever()
