#!/usr/bin/env python3
"""
CLI-прототип платформы онлайн-чаевых — кейс 3 «Вкус-Сервис».

Реализовано:
    1. load_qr(), load_merchant(), load_employee() — чтение справочников CSV.
    2. verify_signature() — криптографическая проверка HMAC-SHA256 (Q-1).
    3. check_exp() — проверка срока действия TTL = 24 ч (Q-2).
    4. Проверка одноразовости nonce (Q-3), статуса мерчанта (Q-4),
       привязки receipt_id (Q-5), диапазона чаевых 0..50% (Q-6).
    5. Правила платежа: лимиты сумм (P-1, P-3), идемпотентность (P-2),
       отмена только из CREATED и запрет отмены из PENDING/SUCCESS (P-4).
    6. emulate_gateway() — 3 исхода шлюза (0..7 SUCCESS, 8 DECLINED, 9 TIMEOUT/PENDING).
    7. calc_amounts() — точный расчёт tip и amount_total.
    8. write_payment() и write_audit() — запись в payments_out.csv и audit_events.csv.
    9. Генерация аналитической отчётности (--report) и автотесты T3-1..T3-5 (--run-tests).
"""
import csv
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import sys

# Секретный ключ загружается из окружения (NFR-3 / 11_ИБ.md), по умолчанию демо-ключ кейса
SECRET = os.environ.get("TIPS_HMAC_SECRET", "demo-secret-k3").encode("utf-8")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_data_file(filename):
    """Ищет CSV-файл в папке 01_данные/ или в текущей директории."""
    candidate_sub = os.path.join(BASE_DIR, "01_данные", filename)
    if os.path.exists(candidate_sub):
        return candidate_sub
    return os.path.join(BASE_DIR, filename)


QR_CSV = _resolve_data_file("qr_links.csv")
MERCHANTS_CSV = _resolve_data_file("merchants.csv")
EMPLOYEES_CSV = _resolve_data_file("employees.csv")
PAYMENTS_CSV = _resolve_data_file("payments.csv")

OUT_CSV = os.path.join(BASE_DIR, "payments_out.csv")
AUDIT_CSV = os.path.join(BASE_DIR, "audit_events.csv")
STATE_JSON = os.path.join(BASE_DIR, "runtime_state.json")

OUT_FIELDS = [
    "payment_id",
    "merchant_id",
    "employee_id",
    "amount",
    "tip",
    "status",
    "timestamp",
]
AUDIT_FIELDS = [
    "event_id",
    "payment_id",
    "qr_id",
    "action",
    "from_status",
    "to_status",
    "amount_total",
    "actor",
    "at",
]

# Опорное время демо-стенда по данным кейса (2025-11-01T18:00:00Z)
DEFAULT_DEMO_NOW = "2025-11-01T18:00:00Z"


def parse_iso_utc(ts_str):
    """Парсит строку ISO 8601 (YYYY-MM-DDTHH:MM:SSZ) в объект datetime UTC."""
    clean = ts_str.strip()
    if clean.endswith("Z"):
        clean = clean[:-1] + "+00:00"
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_qr(qr_id):
    """Загружает запись QR по qr_id из qr_links.csv."""
    if not os.path.exists(QR_CSV):
        return None
    with open(QR_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["qr_id"] == qr_id:
                return row
    return None


def load_merchant(merchant_id):
    """Загружает запись мерчанта по merchant_id из merchants.csv."""
    if not os.path.exists(MERCHANTS_CSV):
        return {"merchant_id": merchant_id, "name": merchant_id, "status": "ACTIVE"}
    with open(MERCHANTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["merchant_id"] == merchant_id:
                return row
    return None


def load_employee(employee_id):
    """Загружает запись сотрудника по employee_id из employees.csv."""
    if not os.path.exists(EMPLOYEES_CSV):
        return {
            "employee_id": employee_id,
            "merchant_id": "m_001",
            "name": employee_id,
            "payment_details": "****0000",
        }
    with open(EMPLOYEES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["employee_id"] == employee_id:
                return row
    return None


def verify_signature(qr):
    """Правило Q-1: проверка подписи HMAC-SHA256 (первые 16 hex-символов)."""
    payload = (
        f"{qr['merchant_id']}|{qr['employee_id']}|"
        f"{qr['receipt_id']}|{qr['nonce']}|{qr['exp']}"
    )
    expected = hmac.new(SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(expected, qr.get("signature", ""))


def check_exp(qr, now_iso=None):
    """Правило Q-2: проверка срока действия QR (exp >= now)."""
    now_str = now_iso or os.environ.get("TIPS_DEMO_NOW", DEFAULT_DEMO_NOW)
    try:
        exp_dt = parse_iso_utc(qr["exp"])
        now_dt = parse_iso_utc(now_str)
        return exp_dt >= now_dt
    except (KeyError, ValueError):
        return False


def calc_amounts(base, pct):
    """Вычисляет сумму чаевых tip и итоговую сумму total."""
    tip = round(float(base) * float(pct) / 100.0, 2)
    total = round(float(base) + tip, 2)
    return tip, total


def emulate_gateway(qr_id, nonce, use_full_md5=False):
    """
    Эмулятор платёжного шлюза:
      0..7 -> SUCCESS (None)
      8    -> DECLINED ("CARD_DECLINED")
      9    -> PENDING ("GATEWAY_TIMEOUT")
    """
    digest = hashlib.md5((qr_id + nonce).encode("utf-8")).hexdigest()
    h = (int(digest, 16) % 10) if use_full_md5 else (int(digest[:4], 16) % 10)
    if h <= 7:
        return "SUCCESS", None
    if h == 8:
        return "DECLINED", "CARD_DECLINED"
    return "PENDING", "GATEWAY_TIMEOUT"


def load_runtime_state():
    """Загружает состояние идемпотентности, использованных nonce и платежей."""
    if os.path.exists(STATE_JSON):
        try:
            with open(STATE_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"idempotency": {}, "used_nonces": [], "payments": {}, "event_seq": 0}


def save_runtime_state(state):
    """Сохраняет состояние выполнения в runtime_state.json."""
    with open(STATE_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def write_payment(payment):
    """Записывает строку платежа в payments_out.csv."""
    new_file = not os.path.exists(OUT_CSV)
    row = {k: payment[k] for k in OUT_FIELDS}
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)


def update_payment_in_csv(payment_id, new_status):
    """Обновляет статус существующего платежа в payments_out.csv (например, при отмене)."""
    if not os.path.exists(OUT_CSV):
        return
    rows = []
    with open(OUT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["payment_id"] == payment_id:
                r["status"] = new_status
            rows.append(r)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rows)


def write_audit(state, payment_id, qr_id, action, from_status, to_status, amount_total, actor="client", at=None):
    """Записывает событие в журнал аудита audit_events.csv (9 полей)."""
    state["event_seq"] = state.get("event_seq", 0) + 1
    event_id = f"evt_{state['event_seq']:04d}"
    event = {
        "event_id": event_id,
        "payment_id": payment_id,
        "qr_id": qr_id,
        "action": action,
        "from_status": from_status,
        "to_status": to_status,
        "amount_total": f"{float(amount_total):.2f}",
        "actor": actor,
        "at": at or DEFAULT_DEMO_NOW,
    }
    new_file = not os.path.exists(AUDIT_CSV)
    with open(AUDIT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(event)
    return event


def process_payment_request(req, state=None, use_full_md5=False):
    """
    Полный цикл обработки запроса на оплату/отмену чаевых с проверкой правил Q-1..Q-6 и P-1..P-4.
    Возвращает кортеж (response_dict, http_code, exit_code).
    """
    own_state = state is None
    if own_state:
        state = load_runtime_state()

    action = req.get("action", "pay")
    now_iso = req.get("now", DEFAULT_DEMO_NOW)

    # Обработка отмены существующего платежа (Правило P-4, Тест T3-5)
    if action == "cancel":
        payment_id = req.get("payment_id")
        stored = state["payments"].get(payment_id)
        if not stored:
            return {
                "status": "ERROR",
                "error_code": "NOT_FOUND",
                "http_status": 404,
                "retryable": False,
            }, 404, 2
        cur_status = stored["status"]
        if cur_status != "CREATED":
            # Правило P-4: отмена из PENDING / SUCCESS / DECLINED запрещена
            return {
                "payment_id": payment_id,
                "status": "ERROR",
                "current_status": cur_status,
                "error_code": "CANCEL_NOT_ALLOWED",
                "http_status": 409,
                "retryable": False,
            }, 409, 1
        stored["status"] = "CANCELED"
        update_payment_in_csv(payment_id, "CANCELED")
        write_audit(
            state,
            payment_id=payment_id,
            qr_id=stored["qr_id"],
            action="payment_canceled",
            from_status=cur_status,
            to_status="CANCELED",
            amount_total=stored["amount_total"],
            actor="client",
            at=now_iso,
        )
        if own_state:
            save_runtime_state(state)
        return {
            "payment_id": payment_id,
            "status": "CANCELED",
            "amount_total": stored["amount_total"],
            "tip_amount": stored["tip_amount"],
            "error_code": None,
        }, 200, 0

    # Правило P-2: проверка идемпотентности (Тест T3-4)
    idem_key = req.get("idempotency_key")
    if idem_key and idem_key in state["idempotency"]:
        cached = dict(state["idempotency"][idem_key])
        cached["idempotent_replay"] = True
        return cached, 200, (0 if cached["status"] in ("SUCCESS", "CREATED") else 1)

    qr_id = req.get("qr_id", "")
    base = float(req.get("base_amount", 1500.0))
    pct = float(req.get("tip_pct", 10.0))

    # Правило P-1: проверка диапазона базовой суммы чека (0 < base <= 1 000 000)
    if base <= 0 or base > 1_000_000:
        return {
            "status": "ERROR",
            "error_code": "AMOUNT_OUT_OF_RANGE",
            "http_status": 422,
            "retryable": False,
        }, 422, 2

    # Правило Q-6: проверка диапазона процента чаевых (0 <= tip_pct <= 50)
    if pct < 0 or pct > 50:
        return {
            "status": "ERROR",
            "error_code": "TIP_OUT_OF_RANGE",
            "http_status": 422,
            "retryable": True,
        }, 422, 2

    qr = load_qr(qr_id)
    if not qr:
        return {
            "status": "ERROR",
            "error_code": "INVALID_QR",
            "http_status": 422,
            "retryable": False,
        }, 422, 2

    # Позволяем в тестовом JSON переопределить поля QR для проверки негативных сценариев (T3-3)
    qr_check = dict(qr)
    if "override_signature" in req:
        qr_check["signature"] = req["override_signature"]
    if "override_exp" in req:
        qr_check["exp"] = req["override_exp"]

    # Правило Q-1: проверка HMAC-SHA256 подписи
    if not verify_signature(qr_check):
        return {
            "status": "ERROR",
            "error_code": "INVALID_QR",
            "http_status": 422,
            "retryable": False,
        }, 422, 2

    # Правило Q-2: проверка TTL (exp >= now)
    if not check_exp(qr_check, now_iso=now_iso):
        return {
            "status": "ERROR",
            "error_code": "QR_EXPIRED",
            "http_status": 410,
            "retryable": True,
        }, 410, 2

    # Правило Q-5: проверка совпадения receipt_id (если передан в запросе)
    if "receipt_id" in req and req["receipt_id"] != qr["receipt_id"]:
        return {
            "status": "ERROR",
            "error_code": "RECEIPT_MISMATCH",
            "http_status": 422,
            "retryable": False,
        }, 422, 2

    # Правило Q-4: проверка статуса мерчанта (ACTIVE)
    merchant = load_merchant(qr["merchant_id"])
    if not merchant or merchant.get("status") != "ACTIVE":
        return {
            "status": "ERROR",
            "error_code": "MERCHANT_BLOCKED",
            "http_status": 403,
            "retryable": False,
        }, 403, 2

    # Правило Q-3: проверка одноразовости nonce
    if qr["nonce"] in state["used_nonces"]:
        return {
            "status": "ERROR",
            "error_code": "QR_USED",
            "http_status": 409,
            "retryable": False,
        }, 409, 2

    tip, total = calc_amounts(base, pct)

    # Правило P-3: проверка итоговой суммы (amount_total <= 2 000 000)
    if total > 2_000_000:
        return {
            "status": "ERROR",
            "error_code": "AMOUNT_OUT_OF_RANGE",
            "http_status": 422,
            "retryable": False,
        }, 422, 2

    payment_id = req.get("payment_id") or f"p_demo_{qr_id[-3:]}"

    # Если запрошено только создание без подтверждения (для сценария отмены T3-5)
    if req.get("auto_confirm", True) is False:
        status = "CREATED"
        error = None
        http_code = 201
    else:
        if "force_gateway_h" in req:
            fh = int(req["force_gateway_h"])
            if fh <= 7:
                status, error = "SUCCESS", None
            elif fh == 8:
                status, error = "DECLINED", "CARD_DECLINED"
            else:
                status, error = "PENDING", "GATEWAY_TIMEOUT"
        else:
            status, error = emulate_gateway(qr_id, qr["nonce"], use_full_md5=use_full_md5)

        if status == "SUCCESS":
            http_code = 200
            if qr["nonce"] not in state["used_nonces"]:
                state["used_nonces"].append(qr["nonce"])
        elif status == "DECLINED":
            http_code = 402
        else:
            http_code = 504

    payment_row = {
        "payment_id": payment_id,
        "merchant_id": qr["merchant_id"],
        "employee_id": qr["employee_id"],
        "amount": f"{base:.2f}",
        "tip": f"{tip:.2f}",
        "status": status,
        "timestamp": now_iso,
    }
    write_payment(payment_row)

    # Запись событий в аудит
    write_audit(
        state,
        payment_id=payment_id,
        qr_id=qr_id,
        action="payment_created",
        from_status="NONE",
        to_status="CREATED",
        amount_total=total,
        actor="client",
        at=now_iso,
    )
    if status != "CREATED":
        act_map = {
            "SUCCESS": "payment_confirmed",
            "DECLINED": "payment_declined",
            "PENDING": "payment_timeout",
        }
        write_audit(
            state,
            payment_id=payment_id,
            qr_id=qr_id,
            action=act_map.get(status, "payment_confirmed"),
            from_status="PENDING",
            to_status=status,
            amount_total=total,
            actor="gateway",
            at=now_iso,
        )

    result = {
        "payment_id": payment_id,
        "status": status,
        "amount_total": total,
        "tip_amount": tip,
        "error_code": error,
    }

    state["payments"][payment_id] = {
        "payment_id": payment_id,
        "qr_id": qr_id,
        "status": status,
        "amount_total": total,
        "tip_amount": tip,
        "error_code": error,
    }
    if idem_key:
        state["idempotency"][idem_key] = result

    if own_state:
        save_runtime_state(state)

    exit_code = 0 if status in ("SUCCESS", "CREATED") else 1
    return result, http_code, exit_code


def generate_reports(merchant_id="m_001", employee_id="e_001"):
    """Формирует 3 разреза отчётности по файлу payments.csv (09_reports.md)."""
    with open(PAYMENTS_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # 1. Отчёт по мерчанту
    m_rows = [r for r in rows if r["merchant_id"] == merchant_id]
    m_succ = [r for r in m_rows if r["status"] == "SUCCESS"]
    m_report = {
        "merchant_id": merchant_id,
        "period": "2025-11",
        "tips_total": round(sum(float(r["tip"]) for r in m_succ), 2),
        "tips_total_all_statuses": round(sum(float(r["tip"]) for r in m_rows), 2),
        "payments_count": len(m_rows),
        "successful_payments_count": len(m_succ),
        "avg_tip_pct": round(
            sum(float(r["tip"]) / float(r["amount"]) * 100 for r in m_succ) / len(m_succ), 2
        )
        if m_succ
        else 0.0,
        "success_rate": round(len(m_succ) / len(m_rows), 4) if m_rows else 0.0,
    }

    # 2. Отчёт по официанту
    e_succ = [r for r in rows if r["employee_id"] == employee_id and r["status"] == "SUCCESS"]
    by_day = {}
    for r in e_succ:
        day = r["timestamp"][:10]
        by_day[day] = round(by_day.get(day, 0.0) + float(r["tip"]), 2)
    top_day = max(by_day.items(), key=lambda x: x[1])[0] if by_day else None
    e_report = {
        "employee_id": employee_id,
        "period": "2025-11",
        "tips_total": round(sum(float(r["tip"]) for r in e_succ), 2),
        "payments_count": len(e_succ),
        "avg_tip_amount": round(sum(float(r["tip"]) for r in e_succ) / len(e_succ), 2)
        if e_succ
        else 0.0,
        "top_day": top_day,
    }

    # 3. Посуточный отчёт по мерчанту
    daily_map = {}
    for r in m_succ:
        day = r["timestamp"][:10]
        daily_map.setdefault(day, []).append(r)
    daily_list = []
    for day in sorted(daily_map.keys()):
        d_rows = daily_map[day]
        daily_list.append(
            {
                "date": day,
                "tips_total": round(sum(float(r["tip"]) for r in d_rows), 2),
                "payments_count": len(d_rows),
                "avg_tip_pct": round(
                    sum(float(r["tip"]) / float(r["amount"]) * 100 for r in d_rows) / len(d_rows),
                    2,
                ),
            }
        )
    daily_report = {"merchant_id": merchant_id, "daily": daily_list}
    return {
        "merchant_report": m_report,
        "employee_report": e_report,
        "daily_report": daily_report,
    }


def run_builtin_tests():
    """Запускает все 5 обязательных тест-сценариев T3-1..T3-5 и выводит отчёт."""
    for p in (OUT_CSV, AUDIT_CSV, STATE_JSON):
        if os.path.exists(p):
            os.remove(p)

    state = load_runtime_state()
    results = []

    # T3-1: Успех (qr_001, base=637.00, tip_pct=5 -> SUCCESS, total=668.85, tip=31.85)
    r1, code1, _ = process_payment_request(
        {"qr_id": "qr_001", "base_amount": 637.00, "tip_pct": 5}, state=state
    )
    t1_ok = (
        r1["status"] == "SUCCESS"
        and r1["amount_total"] == 668.85
        and r1["tip_amount"] == 31.85
        and code1 == 200
    )
    results.append(("T3-1 (Успех)", t1_ok, r1))

    # T3-2: Отказ шлюза (qr_003, base=911.00, tip_pct=15 -> DECLINED, CARD_DECLINED)
    r2, code2, _ = process_payment_request(
        {"qr_id": "qr_003", "base_amount": 911.00, "tip_pct": 15}, state=state
    )
    t2_ok = (
        r2["status"] == "DECLINED"
        and r2["error_code"] == "CARD_DECLINED"
        and r2["amount_total"] == 1047.65
        and code2 == 402
    )
    results.append(("T3-2 (Отказ шлюза)", t2_ok, r2))

    # T3-3: Неверный QR (испорченная подпись -> 422 INVALID_QR, платёж не создан в CSV)
    with open(OUT_CSV, encoding="utf-8") as f:
        lines_before = len(list(csv.DictReader(f)))
    r3, code3, _ = process_payment_request(
        {
            "qr_id": "qr_005",
            "base_amount": 500.00,
            "tip_pct": 10,
            "override_signature": "0000000000000000",
        },
        state=state,
    )
    with open(OUT_CSV, encoding="utf-8") as f:
        lines_after = len(list(csv.DictReader(f)))
    t3_ok = (
        r3.get("error_code") == "INVALID_QR"
        and code3 == 422
        and lines_before == lines_after
    )
    results.append(("T3-3 (Неверный QR)", t3_ok, r3))

    # T3-4: Повтор с тем же idempotency_key -> тот же payment_id, 1 строка в CSV
    req_idem = {
        "qr_id": "qr_002",
        "base_amount": 774.00,
        "tip_pct": 10,
        "idempotency_key": "idem-key-t3-004",
    }
    r4_first, _, _ = process_payment_request(req_idem, state=state)
    r4_second, code4_second, _ = process_payment_request(req_idem, state=state)
    with open(OUT_CSV, encoding="utf-8") as f:
        p002_rows = [
            row for row in csv.DictReader(f) if row["payment_id"] == r4_first["payment_id"]
        ]
    t4_ok = (
        r4_first["payment_id"] == r4_second["payment_id"]
        and code4_second == 200
        and len(p002_rows) == 1
    )
    results.append(("T3-4 (Повтор / Идемпотентность)", t4_ok, r4_second))

    # T3-5: Отмена из CREATED -> CANCELED (200); отмена из PENDING -> CANCEL_NOT_ALLOWED (409)
    r5_create, _, _ = process_payment_request(
        {
            "qr_id": "qr_004",
            "base_amount": 1048.00,
            "tip_pct": 5,
            "auto_confirm": False,
        },
        state=state,
    )
    r5_cancel, code5_cancel, _ = process_payment_request(
        {"action": "cancel", "payment_id": r5_create["payment_id"]}, state=state
    )
    # Создаём платёж в статусе PENDING (qr_010 -> h=9 TIMEOUT/PENDING) и пытаемся отменить
    r5_pend, _, _ = process_payment_request(
        {"qr_id": "qr_010", "base_amount": 1870.00, "tip_pct": 5}, state=state
    )
    r5_cancel_pend, code5_pend, _ = process_payment_request(
        {"action": "cancel", "payment_id": r5_pend["payment_id"]}, state=state
    )
    t5_ok = (
        r5_cancel["status"] == "CANCELED"
        and code5_cancel == 200
        and r5_cancel_pend.get("error_code") == "CANCEL_NOT_ALLOWED"
        and code5_pend == 409
    )
    results.append(
        (
            "T3-5 (Отмена платежа)",
            t5_ok,
            {"cancel_from_created": r5_cancel, "cancel_from_pending": r5_cancel_pend},
        )
    )

    save_runtime_state(state)
    print("=" * 72)
    print("РЕЗУЛЬТАТЫ АВТОМАТИЧЕСКОГО ПРОГОНА 5 ТЕСТ-СЦЕНАРИЕВ (КЕЙС 3)")
    print("=" * 72)
    all_passed = True
    for name, passed, payload in results:
        mark = "PASS [ДА]" if passed else "FAIL [НЕТ]"
        all_passed = all_passed and passed
        print(f"{name:34s} | {mark} | {json.dumps(payload, ensure_ascii=False)}")
    print("=" * 72)
    return 0 if all_passed else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if len(sys.argv) < 2:
        print(
            "Использование:\n"
            "  python 04_прототип.py <qr.json>        — обработка JSON-запроса платежа\n"
            "  python 04_прототип.py --run-tests      — прогон 5 тест-сценариев T3-1..T3-5\n"
            "  python 04_прототип.py --report [m_001] — генерация 3 отчётов по payments.csv"
        )
        sys.exit(1)

    arg1 = sys.argv[1]
    if arg1 == "--run-tests":
        sys.exit(run_builtin_tests())
    if arg1 == "--report":
        m_id = sys.argv[2] if len(sys.argv) > 2 else "m_001"
        e_id = sys.argv[3] if len(sys.argv) > 3 else "e_001"
        print(json.dumps(generate_reports(m_id, e_id), ensure_ascii=False, indent=2))
        sys.exit(0)

    use_full_md5 = "--full-md5" in sys.argv
    with open(arg1, encoding="utf-8") as f:
        req = json.load(f)

    result, _, exit_code = process_payment_request(req, use_full_md5=use_full_md5)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
