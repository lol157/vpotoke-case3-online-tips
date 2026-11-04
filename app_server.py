#!/usr/bin/env python3
"""
HTTP API сервер и интерактивная 4-экранная веб-форма чаевых — кейс 3 «Вкус-Сервис».
Написан на стандартной библиотеке Python (http.server + urllib.parse + json) без внешних зависимостей.
Соответствует спецификации OpenAPI 3.0.3 из файла 05_api_schemas.yaml (порт 8083).
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import json
import os
import re
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Импортируем бизнес-логику из 04_прототип.py
spec = importlib.util.spec_from_file_location(
    "prototype", os.path.join(BASE_DIR, "04_прототип.py")
)
proto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proto)


HTML_DIALOG = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Онлайн-чаевые «Вкус-Сервис»</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #f4f6f9; margin: 0; padding: 24px; color: #1e293b; }
    .card { max-width: 420px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(15,23,42,0.08); }
    .badge { display: inline-block; background: #e0f2fe; color: #0369a1; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; margin-bottom: 12px; }
    h2 { margin: 0 0 8px; font-size: 20px; }
    .row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 15px; }
    .row strong { color: #0f172a; }
    .pct-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin: 16px 0; }
    .pct-btn { padding: 10px 4px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; cursor: pointer; font-weight: 600; }
    .pct-btn.active { background: #2563eb; color: #fff; border-color: #2563eb; }
    .btn { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 12px; }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-danger { background: #ef4444; color: #fff; }
    .screen { display: none; }
    .screen.active { display: block; }
    .status-box { padding: 16px; border-radius: 12px; margin-top: 12px; text-align: center; }
    .status-ok { background: #dcfce7; color: #166534; }
    .status-err { background: #fee2e2; color: #991b1b; }
    .status-wait { background: #fef3c7; color: #92400e; }
  </style>
</head>
<body>
  <div class="card">
    <!-- Экран 1: Приветствие -->
    <div id="s1" class="screen active">
      <span class="badge">Экран 1 из 4 • Приветствие</span>
      <h2 id="m_name">Загрузка...</h2>
      <div class="row"><span>Официант:</span><strong id="e_name">—</strong></div>
      <div class="row"><span>Номер чека:</span><strong id="r_id">—</strong></div>
      <div class="row"><span>Сумма чека:</span><strong id="base_lbl">—</strong></div>
      <button class="btn btn-primary" onclick="goScreen(2)">Продолжить</button>
    </div>

    <!-- Экран 2: Выбор процента чаевых -->
    <div id="s2" class="screen">
      <span class="badge">Экран 2 из 4 • Выбор чаевых</span>
      <h2>Выберите процент чаевых</h2>
      <div class="pct-grid">
        <button class="pct-btn" onclick="setPct(0)">0%</button>
        <button class="pct-btn active" onclick="setPct(5)">5%</button>
        <button class="pct-btn" onclick="setPct(10)">10%</button>
        <button class="pct-btn" onclick="setPct(15)">15%</button>
        <button class="pct-btn" onclick="setPct(20)">20%</button>
      </div>
      <div class="row"><span>Свой процент (0..50%):</span><input id="custom_pct" type="number" min="0" max="50" value="5" style="width:70px;text-align:right;" oninput="setPct(this.value)"></div>
      <div class="row"><span>Сумма чека:</span><strong id="s2_base">0.00 ₽</strong></div>
      <div class="row"><span>Чаевые:</span><strong id="s2_tip">0.00 ₽</strong></div>
      <div class="row"><span>Итого к оплате:</span><strong id="s2_total">0.00 ₽</strong></div>
      <button class="btn btn-primary" onclick="createTip()">Оплатить</button>
    </div>

    <!-- Экран 3: Подтверждение -->
    <div id="s3" class="screen">
      <span class="badge">Экран 3 из 4 • Подтверждение</span>
      <h2>Подтвердите операцию</h2>
      <div class="row"><span>ID платежа:</span><strong id="s3_pid">—</strong></div>
      <div class="row"><span>Сумма чека:</span><strong id="s3_base">—</strong></div>
      <div class="row"><span>Чаевые:</span><strong id="s3_tip">—</strong></div>
      <div class="row"><span>Итого к списанию:</span><strong id="s3_total">—</strong></div>
      <button class="btn btn-primary" onclick="confirmPayment()">Подтвердить оплату</button>
      <button class="btn btn-danger" onclick="cancelPayment()">Отменить</button>
    </div>

    <!-- Экран 4: Результат -->
    <div id="s4" class="screen">
      <span class="badge">Экран 4 из 4 • Результат</span>
      <h2 id="s4_title">Результат</h2>
      <div id="s4_box" class="status-box"></div>
    </div>
  </div>

  <script>
    const params = new URLSearchParams(window.location.search);
    const qrId = params.get('qr') || 'qr_001';
    let qrData = null;
    let tipPct = 5;
    let currentPayment = null;

    function goScreen(n) {
      document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
      document.getElementById('s' + n).classList.add('active');
    }

    function setPct(val) {
      tipPct = parseFloat(val || 0);
      document.getElementById('custom_pct').value = tipPct;
      document.querySelectorAll('.pct-btn').forEach(b => {
        b.classList.toggle('active', b.textContent === tipPct + '%');
      });
      const base = qrData ? qrData.base_amount : 637;
      const tip = Math.round(base * tipPct) / 100;
      const total = Math.round((base + tip) * 100) / 100;
      document.getElementById('s2_base').textContent = base.toFixed(2) + ' ₽';
      document.getElementById('s2_tip').textContent = tip.toFixed(2) + ' ₽';
      document.getElementById('s2_total').textContent = total.toFixed(2) + ' ₽';
    }

    async function loadQR() {
      const res = await fetch('/api/v1/qr/' + qrId);
      const data = await res.json();
      if (!res.ok) {
        goScreen(4);
        document.getElementById('s4_title').textContent = 'Ошибка QR (' + data.error_code + ')';
        const box = document.getElementById('s4_box');
        box.className = 'status-box status-err';
        box.textContent = data.message || data.error_code;
        return;
      }
      qrData = data;
      document.getElementById('m_name').textContent = data.merchant_name;
      document.getElementById('e_name').textContent = data.employee_name;
      document.getElementById('r_id').textContent = data.receipt_id;
      document.getElementById('base_lbl').textContent = data.base_amount.toFixed(2) + ' ₽';
      setPct(5);
    }

    async function createTip() {
      const res = await fetch('/api/v1/tips', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          qr_id: qrData.qr_id,
          receipt_id: qrData.receipt_id,
          base_amount: qrData.base_amount,
          tip_pct: tipPct,
          idempotency_key: 'web-' + qrData.qr_id + '-' + tipPct
        })
      });
      const data = await res.json();
      if (!res.ok) {
        alert('Ошибка: ' + data.error_code);
        return;
      }
      currentPayment = data;
      document.getElementById('s3_pid').textContent = data.payment_id;
      document.getElementById('s3_base').textContent = qrData.base_amount.toFixed(2) + ' ₽';
      document.getElementById('s3_tip').textContent = data.tip_amount.toFixed(2) + ' ₽';
      document.getElementById('s3_total').textContent = data.amount_total.toFixed(2) + ' ₽';
      goScreen(3);
    }

    async function confirmPayment() {
      const res = await fetch('/api/v1/payments/' + currentPayment.payment_id + '/confirm', {method: 'POST'});
      const data = await res.json();
      goScreen(4);
      const box = document.getElementById('s4_box');
      if (data.status === 'SUCCESS') {
        document.getElementById('s4_title').textContent = 'Успешно оплачено';
        box.className = 'status-box status-ok';
        box.textContent = 'Спасибо! Чаевые отправлены (' + data.tip_amount.toFixed(2) + ' ₽).';
      } else if (data.status === 'DECLINED' || res.status === 402) {
        document.getElementById('s4_title').textContent = 'Отказ оплаты';
        box.className = 'status-box status-err';
        box.textContent = 'Оплата не прошла (' + (data.error_code || 'CARD_DECLINED') + '), попробуйте другой способ.';
      } else {
        document.getElementById('s4_title').textContent = 'Обработка платежа';
        box.className = 'status-box status-wait';
        box.textContent = 'Обрабатываем, проверьте через минуту (' + (data.error_code || 'GATEWAY_TIMEOUT') + ').';
      }
    }

    async function cancelPayment() {
      const res = await fetch('/api/v1/payments/' + currentPayment.payment_id + '/cancel', {method: 'POST'});
      const data = await res.json();
      goScreen(4);
      const box = document.getElementById('s4_box');
      if (res.ok) {
        document.getElementById('s4_title').textContent = 'Платёж отменён';
        box.className = 'status-box status-wait';
        box.textContent = 'Платёж ' + data.payment_id + ' отменён (статус CANCELED).';
      } else {
        document.getElementById('s4_title').textContent = 'Отмена невозможна';
        box.className = 'status-box status-err';
        box.textContent = 'Ошибка: ' + data.error_code;
      }
    }

    loadQR();
  </script>
</body>
</html>
"""


class TipsAPIHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов в соответствии с OpenAPI 05_api_schemas.yaml."""

    def log_message(self, format, *args):
        # Тихий режим логов при автотестах
        if os.environ.get("TIPS_VERBOSE_HTTP") == "1":
            super().log_message(format, *args)

    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code, html_text):
        body = html_text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # 1. GET /health
        if path == "/health":
            return self._send_json(200, {"status": "ok"})

        # 2. GET /pay?qr=qr_001 (Интерактивная 4-экранная форма)
        if path == "/pay":
            return self._send_html(200, HTML_DIALOG)

        # 3. GET /api/v1/qr/{qr_id}
        m_qr = re.match(r"^/api/v1/qr/([^/]+)$", path)
        if m_qr:
            qr_id = m_qr.group(1)
            qr = proto.load_qr(qr_id)
            if not qr:
                return self._send_json(
                    404,
                    {
                        "error_code": "NOT_FOUND",
                        "message": f"QR {qr_id} не найден",
                        "retryable": False,
                    },
                )
            if not proto.verify_signature(qr):
                return self._send_json(
                    422,
                    {
                        "error_code": "INVALID_QR",
                        "message": "Подпись QR-кода не совпала с HMAC-SHA256",
                        "retryable": False,
                    },
                )
            now_iso = qs.get("now", [proto.DEFAULT_DEMO_NOW])[0]
            if not proto.check_exp(qr, now_iso=now_iso):
                return self._send_json(
                    410,
                    {
                        "error_code": "QR_EXPIRED",
                        "message": "Срок действия QR-кода (24 ч) истёк",
                        "retryable": True,
                    },
                )
            state = proto.load_runtime_state()
            if qr["nonce"] in state["used_nonces"]:
                return self._send_json(
                    409,
                    {
                        "error_code": "QR_USED",
                        "message": "Одноразовый nonce уже использован",
                        "retryable": False,
                    },
                )
            merchant = proto.load_merchant(qr["merchant_id"])
            if not merchant or merchant.get("status") != "ACTIVE":
                return self._send_json(
                    403,
                    {
                        "error_code": "MERCHANT_BLOCKED",
                        "message": "Мерчант заблокирован или не активирован",
                        "retryable": False,
                    },
                )
            emp = proto.load_employee(qr["employee_id"]) or {"name": qr["employee_id"]}
            idx_num = int(qr_id.split("_")[1]) if "_" in qr_id and qr_id.split("_")[1].isdigit() else 1
            base_amt = float((500 + idx_num * 137) % 3500 + 500)
            return self._send_json(
                200,
                {
                    "qr_id": qr["qr_id"],
                    "merchant_id": qr["merchant_id"],
                    "merchant_name": merchant["name"],
                    "employee_id": qr["employee_id"],
                    "employee_name": emp["name"],
                    "receipt_id": qr["receipt_id"],
                    "base_amount": base_amt,
                    "currency": "RUB",
                    "tip_options": [0, 5, 10, 15, 20],
                    "exp": qr["exp"],
                },
            )

        # 4. GET /api/v1/reports/tips
        if path == "/api/v1/reports/tips":
            role = self.headers.get("X-Role", "merchant")
            if role == "client":
                return self._send_json(
                    403,
                    {
                        "error_code": "FORBIDDEN",
                        "message": "Клиенту запрещён доступ к отчётности",
                        "retryable": False,
                    },
                )
            m_id = qs.get("merchant_id", ["m_001"])[0]
            e_id = qs.get("employee_id", [None])[0]
            if role == "waiter" and not e_id:
                return self._send_json(
                    403,
                    {
                        "error_code": "FORBIDDEN",
                        "message": "Официант может просматривать только свои чаевые (employee_id)",
                        "retryable": False,
                    },
                )
            reps = proto.generate_reports(m_id, e_id or "e_001")
            if e_id:
                return self._send_json(200, reps["employee_report"])
            return self._send_json(200, reps["merchant_report"])

        # 5. GET /api/v1/reports/tips/daily
        if path == "/api/v1/reports/tips/daily":
            m_id = qs.get("merchant_id", ["m_001"])[0]
            reps = proto.generate_reports(m_id, "e_001")
            return self._send_json(200, reps["daily_report"])

        return self._send_json(
            404, {"error_code": "NOT_FOUND", "message": "Эндпоинт не найден", "retryable": False}
        )

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        # 1. POST /api/v1/tips — создание платежа (в статусе CREATED или с автоподтверждением)
        if path == "/api/v1/tips":
            state = proto.load_runtime_state()
            idem_key = body.get("idempotency_key")
            if idem_key and idem_key in state["idempotency"]:
                cached = dict(state["idempotency"][idem_key])
                cached["idempotent_replay"] = True
                return self._send_json(200, cached)

            body_create = dict(body)
            if "auto_confirm" not in body_create:
                body_create["auto_confirm"] = False
            res, code, _ = proto.process_payment_request(body_create, state=state)
            proto.save_runtime_state(state)
            if code >= 400:
                return self._send_json(
                    code,
                    {
                        "error_code": res.get("error_code", "VALIDATION_ERROR"),
                        "message": f"Ошибка проверки: {res.get('error_code')}",
                        "retryable": res.get("retryable", False),
                    },
                )
            return self._send_json(code, res)

        # 2. POST /api/v1/payments/{id}/confirm — подтверждение платежа в шлюзе
        m_conf = re.match(r"^/api/v1/payments/([^/]+)/confirm$", path)
        if m_conf:
            pid = m_conf.group(1)
            state = proto.load_runtime_state()
            stored = state["payments"].get(pid)
            if not stored:
                return self._send_json(
                    404,
                    {"error_code": "NOT_FOUND", "message": "Платёж не найден", "retryable": False},
                )
            if stored["status"] in ("CANCELED", "DECLINED"):
                return self._send_json(
                    409,
                    {
                        "error_code": "INVALID_STATE_TRANSITION",
                        "message": f"Нельзя подтвердить платёж из статуса {stored['status']}",
                        "retryable": False,
                    },
                )
            qr = proto.load_qr(stored["qr_id"])
            status, err = proto.emulate_gateway(qr["qr_id"], qr["nonce"])
            stored["status"] = status
            stored["error_code"] = err
            proto.update_payment_in_csv(pid, status)
            proto.write_audit(
                state,
                payment_id=pid,
                qr_id=qr["qr_id"],
                action="payment_confirmed" if status == "SUCCESS" else "payment_declined",
                from_status="PENDING",
                to_status=status,
                amount_total=stored["amount_total"],
                actor="gateway",
            )
            if status == "SUCCESS" and qr["nonce"] not in state["used_nonces"]:
                state["used_nonces"].append(qr["nonce"])
            for k, v in state["idempotency"].items():
                if v.get("payment_id") == pid:
                    v["status"] = status
                    v["error_code"] = err
            proto.save_runtime_state(state)

            if status == "SUCCESS":
                return self._send_json(200, stored)
            if status == "DECLINED":
                return self._send_json(
                    402,
                    {
                        "payment_id": pid,
                        "status": "DECLINED",
                        "error_code": "CARD_DECLINED",
                        "message": "Отказ платёжного шлюза по карте",
                        "retryable": True,
                    },
                )
            return self._send_json(
                504,
                {
                    "payment_id": pid,
                    "status": "PENDING",
                    "error_code": "GATEWAY_TIMEOUT",
                    "message": "Таймаут шлюза, платёж в обработке",
                    "retryable": True,
                },
            )

        # 3. POST /api/v1/payments/{id}/cancel — отмена платежа до подтверждения
        m_canc = re.match(r"^/api/v1/payments/([^/]+)/cancel$", path)
        if m_canc:
            pid = m_canc.group(1)
            state = proto.load_runtime_state()
            res, code, _ = proto.process_payment_request(
                {"action": "cancel", "payment_id": pid}, state=state
            )
            proto.save_runtime_state(state)
            if code >= 400:
                return self._send_json(
                    code,
                    {
                        "error_code": res.get("error_code", "CANCEL_NOT_ALLOWED"),
                        "message": "Отмена разрешена только из статуса CREATED",
                        "retryable": False,
                    },
                )
            return self._send_json(200, res)

        return self._send_json(
            404, {"error_code": "NOT_FOUND", "message": "Эндпоинт не найден", "retryable": False}
        )


def run_server(port=8083):
    server = HTTPServer(("127.0.0.1", port), TipsAPIHandler)
    print(f"Сервер онлайн-чаевых запущен: http://localhost:{port}")
    print(f"Диалоговая форма выбора чаевых: http://localhost:{port}/pay?qr=qr_001")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
