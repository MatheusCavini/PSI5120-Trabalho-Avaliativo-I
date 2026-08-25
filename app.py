#!/usr/bin/env python3
"""Aplicação web do Trabalho Avaliativo 1 da PSI5120 - Matheus Cavini.

Adaptada a partir do app.py da Aula 4 (mesma base: apenas biblioteca padrão
Python, mesmo padrão de contador persistido e de endpoints), com página
personalizada para este trabalho e com o acréscimo do endpoint /work, que
substitui o papel do endpoint de teste do exemplo oficial php-apache
(citado nas referências do trabalho) por uma versão em Python puro.

Endpoints:
- /            página HTML
- /api/status  estado em JSON
- /health      resposta simples de saúde
- /work        consome CPU de forma controlada, usada para acionar o HPA

O contador é persistido no diretório definido por DATA_DIR, por padrão /data.
A mensagem é lida de PSI5120_MESSAGE ou, se MESSAGE_FILE estiver definido,
do arquivo indicado por MESSAGE_FILE.
A intensidade do endpoint /work é controlada por WORK_ITERATIONS.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import os
import socket
import sys
import time

APP_PORT = int(os.environ.get("APP_PORT", "8080"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
AUTOR = os.environ.get("PSI5120_AUTOR", "Matheus Cavini")
MESSAGE = os.environ.get("PSI5120_MESSAGE", f"Trabalho Avaliativo 1 - PSI5120 - {AUTOR}")
MESSAGE_FILE = os.environ.get("MESSAGE_FILE", "")
COUNTER_FILE = DATA_DIR / "counter.txt"

# Quantidade de iterações do laço de /work. Controla o tempo de CPU gasto
# por requisição: quanto maior, mais tempo cada chamada ocupa um núcleo de
# CPU. O valor padrão foi escolhido para gerar uma carga perceptível sem
# travar a resposta por muito tempo; pode ser recalibrado por ambiente
# através da variável de ambiente WORK_ITERATIONS, sem alterar o código.
WORK_ITERATIONS = int(os.environ.get("WORK_ITERATIONS", "2000000"))


def log(message: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    print(f"{now} {message}", flush=True)


def read_message() -> str:
    if MESSAGE_FILE:
        try:
            content = Path(MESSAGE_FILE).read_text(encoding="utf-8").strip()
            if content:
                return content
        except FileNotFoundError:
            return f"{MESSAGE} (arquivo de mensagem nao encontrado: {MESSAGE_FILE})"
        except OSError as exc:
            return f"{MESSAGE} (erro ao ler MESSAGE_FILE: {exc})"
    return MESSAGE


def increment_counter() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        current = int(COUNTER_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        current = 0
    current += 1
    COUNTER_FILE.write_text(str(current), encoding="utf-8")
    return current


def cpu_burn(iterations: int) -> float:
    """Executa um cálculo matemático repetitivo, sem efeito colateral,
    apenas para consumir CPU de forma controlada e mensurável pelo
    Metrics Server. É o equivalente, em Python puro, ao script PHP que
    calcula raízes quadradas em loop na imagem registry.k8s.io/hpa-example
    usada no walkthrough oficial do Kubernetes."""
    total = 0.0
    x = 0.0001
    for i in range(iterations):
        x = math.sqrt(x + i)
        total += x
    return total


class Handler(BaseHTTPRequestHandler):
    server_version = "PSI5120Trab1/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        # /health e /work não incrementam o contador: /health porque é uma
        # verificação de infraestrutura, e /work porque é chamado em alta
        # frequência pelo gerador de carga e não deve competir por I/O de
        # disco com o cálculo de CPU que está sendo medido.
        if self.path == "/health":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
            return

        if self.path == "/work":
            start = time.monotonic()
            result = cpu_burn(WORK_ITERATIONS)
            elapsed_ms = (time.monotonic() - start) * 1000
            log(f"work path={self.path} client={self.client_address[0]} elapsed_ms={elapsed_ms:.2f}")
            body = f"work done result={result:.4f} elapsed_ms={elapsed_ms:.2f}\n".encode("utf-8")
            self._send(200, body, "text/plain; charset=utf-8")
            return

        counter = increment_counter()
        message = read_message()
        log(f"request path={self.path} client={self.client_address[0]} counter={counter}")

        if self.path == "/api/status":
            payload = {
                "service": "psi5120-trab1-webapp",
                "autor": AUTOR,
                "status": "ok",
                "message": message,
                "counter": counter,
                "hostname": socket.gethostname(),
                "data_dir": str(DATA_DIR),
                "message_file": MESSAGE_FILE or None,
                "work_iterations": WORK_ITERATIONS,
                "time_utc": datetime.now(timezone.utc).isoformat(),
            }
            self._send(200, json.dumps(payload, indent=2).encode("utf-8") + b"\n", "application/json; charset=utf-8")
            return

        if self.path == "/":
            html = f"""<!doctype html>
<html lang=\"pt-BR\"><head>
<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>PSI5120 · Trabalho Avaliativo 1</title>
<style>
:root {{--bg:#09090b;--surface:rgba(24,24,27,.82);--surface2:#18181b;--border:rgba(255,255,255,.09);--text:#fafafa;--muted:#a1a1aa;--accent:#60a5fa;--accent2:#818cf8;--success:#4ade80}}
* {{box-sizing:border-box}} body {{margin:0;min-height:100vh;padding:32px 20px;color:var(--text);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(circle at 15% 10%,rgba(96,165,250,.16),transparent 30%),radial-gradient(circle at 85% 85%,rgba(129,140,248,.13),transparent 30%),var(--bg)}}
.container {{width:min(860px,100%);margin:auto}} .hero {{margin-bottom:18px;padding:8px 4px}}
.badge {{display:inline-flex;align-items:center;gap:8px;padding:6px 11px;border:1px solid rgba(96,165,250,.25);border-radius:999px;color:#bfdbfe;background:rgba(96,165,250,.08);font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase}}
.dot {{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 12px rgba(74,222,128,.7)}}
h1 {{margin:18px 0 8px;font-size:clamp(32px,6vw,52px);line-height:1.05;letter-spacing:-.045em;background:linear-gradient(120deg,#fff,#bfdbfe 45%,#a5b4fc);-webkit-background-clip:text;background-clip:text;color:transparent}}
.subtitle {{margin:0;max-width:700px;color:var(--muted);font-size:16px;line-height:1.65}}
.card {{overflow:hidden;border:1px solid var(--border);border-radius:22px;background:var(--surface);backdrop-filter:blur(18px);box-shadow:0 24px 80px rgba(0,0,0,.35)}}
.card-header {{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:22px 26px;border-bottom:1px solid var(--border)}}
.card-title {{margin:0;font-size:15px;font-weight:700}} .status {{display:inline-flex;align-items:center;gap:7px;color:#bbf7d0;font-size:12px;font-weight:700}} .status .dot {{width:6px;height:6px}}
.content {{padding:26px}} .message {{margin-bottom:24px;padding:18px 20px;border-radius:14px;background:var(--surface2);border:1px solid var(--border)}}
.message-label {{color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:7px}} .message-value {{font-size:17px;font-weight:600}}
.grid {{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}} .stat {{padding:17px;border:1px solid var(--border);border-radius:14px;background:rgba(255,255,255,.025)}} .stat-label {{color:var(--muted);font-size:12px;margin-bottom:7px}} .stat-value {{overflow-wrap:anywhere;font-size:14px;font-weight:650}} .counter {{color:#bfdbfe;font-size:23px}}
.endpoints {{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px;padding-top:20px;border-top:1px solid var(--border)}} code {{padding:6px 10px;border-radius:8px;background:#27272a;border:1px solid rgba(255,255,255,.06);color:#bfdbfe;font-family:monospace;font-size:12px}}
footer {{padding:18px 4px 0;color:#71717a;text-align:center;font-size:12px}} @media(max-width:600px) {{body{{padding:20px 14px}}.content,.card-header{{padding:20px}}.grid{{grid-template-columns:1fr}}}}
</style></head>
<body><main class=\"container\">
<section class=\"hero\"><span class=\"badge\"><span class=\"dot\"></span> PSI5120 · Computação em Nuvem</span>
<h1>Trabalho Avaliativo 1</h1><p class=\"subtitle\">Autoescalamento Horizontal de Pods (HPA) com Kubernetes local (Minikube) e Amazon EKS.</p></section>
<section class=\"card\"><div class=\"card-header\"><h2 class=\"card-title\">Informações da aplicação</h2><span class=\"status\"><span class=\"dot\"></span> Serviço online</span></div>
<div class=\"content\"><div class=\"message\"><div class=\"message-label\">Mensagem</div><div class=\"message-value\">{message}</div></div>
<div class=\"grid\"><div class=\"stat\"><div class=\"stat-label\">Contador de acessos</div><div class=\"stat-value counter\">{counter}</div></div>
<div class=\"stat\"><div class=\"stat-label\">Hostname do Pod</div><div class=\"stat-value\">{socket.gethostname()}</div></div>
<div class=\"stat\"><div class=\"stat-label\">Diretório de dados</div><div class=\"stat-value\">{DATA_DIR}</div></div>
<div class=\"stat\"><div class=\"stat-label\">Autor</div><div class=\"stat-value\">{AUTOR}</div></div></div>
<div class=\"endpoints\"><code>/</code><code>/api/status</code><code>/health</code><code>/work</code></div></div></section>
<footer>Aplicação Python · Kubernetes · HPA</footer></main></body></html>
""".encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        self._send(404, b"not found\n", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:
        # evitar log duplicado do BaseHTTPRequestHandler
        return


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler)
    log(f"starting service port={APP_PORT} data_dir={DATA_DIR} hostname={socket.gethostname()} work_iterations={WORK_ITERATIONS} autor={AUTOR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutdown requested")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())