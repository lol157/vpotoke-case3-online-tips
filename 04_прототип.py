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
OUT_CSV = os.path.join(BASE_DIR, "payments_out.csv")
OUT_FIELDS = ["payment_id", "merchant_id", "employee_id", "amount", "tip", "status", "timestamp"]


def load_qr(qr_id):
    with open(QR_CSV, encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r["qr_id"] == qr_id), None)


def verify_signature(qr):
    payload = f"{qr['merchant_id']}|{qr['employee_id']}|{qr['receipt_id']}|{qr['nonce']}|{qr['exp']}"
    expected = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(expected, qr["signature"])


def check_exp(qr, now="2025-11-01T18:00:00Z"):
    return qr["exp"] >= now


def calc_amounts(base, pct):
    tip = round(base * pct / 100, 2)
    return tip, round(base + tip, 2)


def emulate_gateway(qr_id, nonce):
    h = int(hashlib.md5((qr_id + nonce).encode()).hexdigest()[:4], 16) % 10
    if h == 8:
        return "DECLINED", "CARD_DECLINED"
    if h == 9:
        return "PENDING", "GATEWAY_TIMEOUT"
    return "SUCCESS", None


def write_payment(payment):
    exists = os.path.exists(OUT_CSV)
    if exists and payment["payment_id"] in open(OUT_CSV, encoding="utf-8").read():
        return
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(payment)


def main():
    if len(sys.argv) < 2:
        sys.exit("Использование: python 04_прототип.py qr.json")

    with open(sys.argv[1], encoding="utf-8") as f:
        req = json.load(f)

    if req.get("action") == "cancel":
        print(json.dumps({"payment_id": req["payment_id"], "status": "ERROR", "error_code": "CANCEL_NOT_ALLOWED", "http_status": 409}, ensure_ascii=False))
        sys.exit(1)

    qr_id = req["qr_id"]
    base = float(req.get("base_amount", 1500))
    pct = float(req.get("tip_pct", 10))
    now = req.get("now", "2025-11-01T18:00:00Z")

    qr = load_qr(qr_id)
    if qr and "signature" in req:
        qr["signature"] = req["signature"]

    if not qr or not verify_signature(qr):
        print(json.dumps({"status": "ERROR", "error_code": "INVALID_QR"}, ensure_ascii=False))
        sys.exit(2)

    if not check_exp(qr, now):
        print(json.dumps({"status": "ERROR", "error_code": "QR_EXPIRED"}, ensure_ascii=False))
        sys.exit(2)

    tip, total = calc_amounts(base, pct)
    status, error = emulate_gateway(qr_id, qr["nonce"])
    payment_id = req.get("idempotency_key") or f"p_demo_{qr_id[-3:]}"

    write_payment({
        "payment_id": payment_id,
        "merchant_id": qr["merchant_id"],
        "employee_id": qr["employee_id"],
        "amount": f"{base:.2f}",
        "tip": f"{tip:.2f}",
        "status": status,
        "timestamp": now,
    })

    print(json.dumps({
        "payment_id": payment_id,
        "status": status,
        "amount_total": total,
        "tip_amount": tip,
        "error_code": error,
    }, ensure_ascii=False, indent=2))
    sys.exit(0 if status == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
