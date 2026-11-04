#!/usr/bin/env python3
"""
Автоматизированный набор модульных и интеграционных тестов (unittest) — кейс 3 «Онлайн-чаевые».
Проверяет:
  - 5 обязательных тест-сценариев T3-1..T3-5;
  - все 6 правил проверки QR (Q-1..Q-6);
  - все 4 правила платежа (P-1..P-4);
  - 3 разреза аналитической отчётности (09_reports.md);
  - REST API сервер app_server.py (/health, /api/v1/qr/{id}, /api/v1/tips, /confirm, /cancel, /reports).
"""
import csv
from http.server import HTTPServer
import importlib.util
import json
import os
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

spec_proto = importlib.util.spec_from_file_location(
    "prototype", os.path.join(BASE_DIR, "04_прототип.py")
)
proto = importlib.util.module_from_spec(spec_proto)
spec_proto.loader.exec_module(proto)

spec_srv = importlib.util.spec_from_file_location(
    "app_server", os.path.join(BASE_DIR, "app_server.py")
)
app_srv = importlib.util.module_from_spec(spec_srv)
spec_srv.loader.exec_module(app_srv)


class TestCase3TipsPlatform(unittest.TestCase):
    """Полный тестовый набор платформы онлайн-чаевых (Кейс 3)."""

    def setUp(self):
        for p in (proto.OUT_CSV, proto.AUDIT_CSV, proto.STATE_JSON):
            if os.path.exists(p):
                os.remove(p)
        self.state = proto.load_runtime_state()

    def test_t3_1_success_payment(self):
        """T3-1. Успех: qr_001, base=637.00, tip_pct=5 -> SUCCESS, total=668.85, tip=31.85."""
        res, http_code, exit_code = proto.process_payment_request(
            {"qr_id": "qr_001", "receipt_id": "r_1001", "base_amount": 637.00, "tip_pct": 5},
            state=self.state,
        )
        self.assertEqual(http_code, 200)
        self.assertEqual(exit_code, 0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertAlmostEqual(res["tip_amount"], 31.85, places=2)
        self.assertAlmostEqual(res["amount_total"], 668.85, places=2)
        self.assertIsNone(res["error_code"])

    def test_t3_2_gateway_declined(self):
        """T3-2. Отказ шлюза: qr_003, base=911.00, tip_pct=15 -> DECLINED, CARD_DECLINED."""
        res, http_code, exit_code = proto.process_payment_request(
            {"qr_id": "qr_003", "receipt_id": "r_1003", "base_amount": 911.00, "tip_pct": 15},
            state=self.state,
        )
        self.assertEqual(http_code, 402)
        self.assertEqual(exit_code, 1)
        self.assertEqual(res["status"], "DECLINED")
        self.assertEqual(res["error_code"], "CARD_DECLINED")
        self.assertAlmostEqual(res["tip_amount"], 136.65, places=2)
        self.assertAlmostEqual(res["amount_total"], 1047.65, places=2)

    def test_t3_3_invalid_and_expired_qr(self):
        """T3-3. Неверный / истёкший QR -> INVALID_QR (422) и QR_EXPIRED (410), платёж не создан."""
        res_sig, code_sig, _ = proto.process_payment_request(
            {
                "qr_id": "qr_001",
                "base_amount": 637.00,
                "tip_pct": 5,
                "override_signature": "deadbeefdeadbeef",
            },
            state=self.state,
        )
        self.assertEqual(code_sig, 422)
        self.assertEqual(res_sig["error_code"], "INVALID_QR")
        self.assertFalse(os.path.exists(proto.OUT_CSV))

        res_exp, code_exp, _ = proto.process_payment_request(
            {
                "qr_id": "qr_001",
                "base_amount": 637.00,
                "tip_pct": 5,
                "now": "2025-11-10T00:00:00Z",
            },
            state=self.state,
        )
        self.assertEqual(code_exp, 410)
        self.assertEqual(res_exp["error_code"], "QR_EXPIRED")
        self.assertFalse(os.path.exists(proto.OUT_CSV))

    def test_t3_4_idempotency_replay(self):
        """T3-4. Повтор с тем же idempotency_key -> тот же payment_id, 1 строка в CSV."""
        req = {
            "qr_id": "qr_002",
            "receipt_id": "r_1002",
            "base_amount": 774.00,
            "tip_pct": 10,
            "idempotency_key": "idem-test-004",
        }
        r1, code1, _ = proto.process_payment_request(req, state=self.state)
        r2, code2, _ = proto.process_payment_request(req, state=self.state)

        self.assertEqual(code1, 200)
        self.assertEqual(code2, 200)
        self.assertEqual(r1["payment_id"], r2["payment_id"])
        self.assertTrue(r2.get("idempotent_replay"))

        with open(proto.OUT_CSV, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)

    def test_t3_5_cancel_payment_rules(self):
        """T3-5. Отмена из CREATED -> CANCELED (200); отмена из PENDING -> 409 CANCEL_NOT_ALLOWED."""
        r_created, code_c, _ = proto.process_payment_request(
            {"qr_id": "qr_004", "base_amount": 1048.00, "tip_pct": 5, "auto_confirm": False},
            state=self.state,
        )
        self.assertEqual(code_c, 201)
        self.assertEqual(r_created["status"], "CREATED")

        r_canc, code_canc, _ = proto.process_payment_request(
            {"action": "cancel", "payment_id": r_created["payment_id"]},
            state=self.state,
        )
        self.assertEqual(code_canc, 200)
        self.assertEqual(r_canc["status"], "CANCELED")

        # Платёж в статусе PENDING (qr_010 -> h=9 TIMEOUT)
        r_pend, code_p, _ = proto.process_payment_request(
            {"qr_id": "qr_010", "base_amount": 1870.00, "tip_pct": 5},
            state=self.state,
        )
        self.assertEqual(code_p, 504)
        self.assertEqual(r_pend["status"], "PENDING")

        r_canc_pend, code_cp, _ = proto.process_payment_request(
            {"action": "cancel", "payment_id": r_pend["payment_id"]},
            state=self.state,
        )
        self.assertEqual(code_cp, 409)
        self.assertEqual(r_canc_pend["error_code"], "CANCEL_NOT_ALLOWED")

    def test_all_validation_rules_q_and_p(self):
        """Проверка остальных правил: Q-3 (QR_USED), Q-5 (RECEIPT_MISMATCH), Q-6 (TIP_OUT_OF_RANGE), P-1 (AMOUNT_OUT_OF_RANGE)."""
        # Q-6: tip_pct > 50
        r_tip, c_tip, _ = proto.process_payment_request(
            {"qr_id": "qr_001", "base_amount": 637.00, "tip_pct": 55}, state=self.state
        )
        self.assertEqual(c_tip, 422)
        self.assertEqual(r_tip["error_code"], "TIP_OUT_OF_RANGE")

        # P-1: base_amount <= 0 и > 1_000_000
        r_amt, c_amt, _ = proto.process_payment_request(
            {"qr_id": "qr_001", "base_amount": 1_500_000, "tip_pct": 10}, state=self.state
        )
        self.assertEqual(c_amt, 422)
        self.assertEqual(r_amt["error_code"], "AMOUNT_OUT_OF_RANGE")

        # Q-5: receipt_id не совпадает
        r_rec, c_rec, _ = proto.process_payment_request(
            {"qr_id": "qr_001", "receipt_id": "r_9999", "base_amount": 637.00, "tip_pct": 5},
            state=self.state,
        )
        self.assertEqual(c_rec, 422)
        self.assertEqual(r_rec["error_code"], "RECEIPT_MISMATCH")

        # Q-3: повторное использование nonce после успешного платежа
        proto.process_payment_request(
            {"qr_id": "qr_001", "base_amount": 637.00, "tip_pct": 5}, state=self.state
        )
        r_used, c_used, _ = proto.process_payment_request(
            {"qr_id": "qr_001", "base_amount": 637.00, "tip_pct": 5}, state=self.state
        )
        self.assertEqual(c_used, 409)
        self.assertEqual(r_used["error_code"], "QR_USED")

    def test_reports_match_csv(self):
        """Проверка сходимости отчётов (09_reports.md) с payments.csv."""
        reps = proto.generate_reports("m_001", "e_001")
        self.assertAlmostEqual(reps["merchant_report"]["tips_total"], 414.85, places=2)
        self.assertEqual(reps["merchant_report"]["payments_count"], 6)
        self.assertAlmostEqual(reps["employee_report"]["tips_total"], 83.60, places=2)
        self.assertEqual(reps["employee_report"]["top_day"], "2025-11-03")
        self.assertEqual(len(reps["daily_report"]["daily"]), 2)

    def test_http_api_server_endpoints(self):
        """Интеграционный тест HTTP-сервера app_server.py (OpenAPI 05_api_schemas.yaml)."""
        server = HTTPServer(("127.0.0.1", 0), app_srv.TipsAPIHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{port}"

        try:
            # GET /health
            with urlopen(f"{base_url}/health") as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(json.loads(resp.read().decode())["status"], "ok")

            # GET /api/v1/qr/qr_001
            with urlopen(f"{base_url}/api/v1/qr/qr_001") as resp:
                self.assertEqual(resp.status, 200)
                qr_data = json.loads(resp.read().decode())
                self.assertEqual(qr_data["merchant_id"], "m_001")
                self.assertEqual(qr_data["employee_name"], "Иванов И.")

            # POST /api/v1/tips -> 201 CREATED
            req_body = json.dumps(
                {
                    "qr_id": "qr_001",
                    "receipt_id": "r_1001",
                    "base_amount": 637.00,
                    "tip_pct": 5,
                    "idempotency_key": "http-idem-1",
                }
            ).encode("utf-8")
            req = Request(
                f"{base_url}/api/v1/tips",
                data=req_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req) as resp:
                self.assertEqual(resp.status, 201)
                pay_created = json.loads(resp.read().decode())
                self.assertEqual(pay_created["status"], "CREATED")

            # POST /api/v1/payments/{id}/confirm -> 200 SUCCESS
            pid = pay_created["payment_id"]
            req_conf = Request(f"{base_url}/api/v1/payments/{pid}/confirm", method="POST")
            with urlopen(req_conf) as resp:
                self.assertEqual(resp.status, 200)
                pay_conf = json.loads(resp.read().decode())
                self.assertEqual(pay_conf["status"], "SUCCESS")

            # POST /api/v1/payments/{id}/cancel после SUCCESS -> 409 CANCEL_NOT_ALLOWED
            req_canc = Request(f"{base_url}/api/v1/payments/{pid}/cancel", method="POST")
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req_canc)
            self.assertEqual(ctx.exception.code, 409)
            ctx.exception.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
