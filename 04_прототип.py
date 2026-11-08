#!/usr/bin/env python3
"""
CLI-прототип платформы чаевых — кейс 3.

TODO:
    1. load_qr() — читать qr_links.csv.
    2. verify_signature() — HMAC-SHA256.
    3. check_exp() — TTL.
    4. emulate_gateway() — 4 сценария (0..7 SUCCESS, 8 DECLINED, 9 TIMEOUT).
    5. calc_amounts() — tip + total.
    6. write_payment() — append в payments_out.csv.
"""
import csv
import hashlib
import hmac
import json
import os
import sys

SECRET = b"demo-secret-k3"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QR_CSV = os.path.join(BASE_DIR, "01_данные", "qr_links.csv")
if not os.path.exists(QR_CSV):
    QR_CSV = os.path.join(BASE_DIR, "qr_links.csv")
OUT_CSV = os.path.join(BASE_DIR, "payments_out.csv")

OUT_FIELDS = ["payment_id", "merchant_id", "employee_id", "amount", "tip", "status", "timestamp"]


def load_qr(qr_id):
    with open(QR_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["qr_id"] == qr_id:
                return row
    return None


def verify_signature(qr):
    payload = f"{qr['merchant_id']}|{qr['employee_id']}|{qr['receipt_id']}|{qr['nonce']}|{qr['exp']}"
    expected = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(expected, qr["signature"])


def check_exp(qr, now="2025-11-01T18:00:00Z"):
    """Проверка TTL: exp >= now."""
    return qr["exp"] >= now


def calc_amounts(base, pct):
    tip = round(base * pct / 100, 2)
    return tip, round(base + tip, 2)


def emulate_gateway(qr_id, nonce):
    """0..7 SUCCESS, 8 DECLINED, 9 TIMEOUT."""
    h = int(hashlib.md5((qr_id + nonce).encode()).hexdigest()[:4], 16) % 10
    if h <= 7:
        return "SUCCESS", None
    if h == 8:
        return "DECLINED", "CARD_DECLINED"
    return "PENDING", "GATEWAY_TIMEOUT"


def find_payment(payment_id):
    if not os.path.exists(OUT_CSV):
        return None
    with open(OUT_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["payment_id"] == payment_id:
                return row
    return None


def write_payment(payment):
    new_file = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(payment)


def cancel_payment(payment_id):
    rows = []
    target = None
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["payment_id"] == payment_id:
                    target = row
                rows.append(row)
    if not target:
        return {"status": "ERROR", "error_code": "NOT_FOUND"}, 2
    if target["status"] != "CREATED":
        return {"payment_id": payment_id, "status": "ERROR", "error_code": "CANCEL_NOT_ALLOWED", "http_status": 409}, 1
    target["status"] = "CANCELED"
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return {"payment_id": payment_id, "status": "CANCELED", "error_code": None}, 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print("Использование: python 04_прототип.py qr.json")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        req = json.load(f)

    # Сценарий отмены (T3-5)
    if req.get("action") == "cancel":
        res, code = cancel_payment(req["payment_id"])
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(code)

    qr_id = req["qr_id"]
    base = float(req.get("base_amount", 1500))
    pct = float(req.get("tip_pct", 10))
    now = req.get("now", "2025-11-01T18:00:00Z")

    if base <= 0 or base > 1_000_000:
        print(json.dumps({"status": "ERROR", "error_code": "AMOUNT_OUT_OF_RANGE"}, ensure_ascii=False))
        sys.exit(2)

    if pct < 0 or pct > 50:
        print(json.dumps({"status": "ERROR", "error_code": "TIP_OUT_OF_RANGE"}, ensure_ascii=False))
        sys.exit(2)

    qr = load_qr(qr_id)
    if not qr:
        print(json.dumps({"status": "ERROR", "error_code": "INVALID_QR"}, ensure_ascii=False))
        sys.exit(2)

    if "signature" in req:
        qr["signature"] = req["signature"]

    if not verify_signature(qr):
        print(json.dumps({"status": "ERROR", "error_code": "INVALID_QR"}, ensure_ascii=False))
        sys.exit(2)

    if not check_exp(qr, now):
        print(json.dumps({"status": "ERROR", "error_code": "QR_EXPIRED"}, ensure_ascii=False))
        sys.exit(2)

    tip, total = calc_amounts(base, pct)
    payment_id = req.get("idempotency_key") or f"p_demo_{qr_id[-3:]}"

    # Идемпотентность (P-2, T3-4): если платёж с таким ключом уже создан — вернуть его без дубля
    existing = find_payment(payment_id)
    if existing:
        ex_tip = float(existing["tip"])
        ex_total = round(float(existing["amount"]) + ex_tip, 2)
        print(json.dumps({
            "payment_id": existing["payment_id"],
            "status": existing["status"],
            "amount_total": ex_total,
            "tip_amount": ex_tip,
            "error_code": None,
        }, ensure_ascii=False, indent=2))
        sys.exit(0 if existing["status"] in ("SUCCESS", "CREATED") else 1)

    if req.get("confirm", True) is False:
        status, error = "CREATED", None
    else:
        status, error = emulate_gateway(qr_id, qr["nonce"])

    payment = {
        "payment_id": payment_id,
        "merchant_id": qr["merchant_id"],
        "employee_id": qr["employee_id"],
        "amount": f"{base:.2f}",
        "tip": f"{tip:.2f}",
        "status": status,
        "timestamp": now,
    }
    write_payment(payment)

    print(json.dumps({
        "payment_id": payment["payment_id"],
        "status": status,
        "amount_total": total,
        "tip_amount": tip,
        "error_code": error,
    }, ensure_ascii=False, indent=2))

    sys.exit(0 if status in ("SUCCESS", "CREATED") else 1)


if __name__ == "__main__":
    main()
