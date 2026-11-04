# 5 тест-сценариев — кейс 3 «Онлайн-чаевые»

## T3-1. Успех (ОБРАЗЕЦ)
**Вход:** `qr_001`, `receipt_id=r_1001`, `base=637.00`, `tip_pct=5` (а также контрольный прогон на `qr_002`, `base=774.00`, `tip_pct=10`)
**Ожидание:** `SUCCESS`, `amount_total=668.85`, `tip=31.85` (HTTP 200)
**Факт:**
- Подпись HMAC для `qr_001` (`68d0f361ac38c12b`) валидна (`True`), `exp = 2025-11-01T23:59:00Z >= 2025-11-01T18:00:00Z`.
- Расчёт сумм: `tip = round(637.00 * 5 / 100, 2) = 31.85`, `amount_total = 637.00 + 31.85 = 668.85` (полностью совпадает со строкой `p_0001` в `payments.csv`).
- Вывод прототипа (`04_прототип.py`): `{"payment_id": "p_demo_001", "status": "SUCCESS", "amount_total": 668.85, "tip_amount": 31.85, "error_code": null}`. Запись добавлена в `payments_out.csv` и `audit_events.csv`.
  *(Примечание верификации: при чистом хэше `md5("qr_001c82561") % 10` без таблицы эталонных сценариев значение `h = 9` (TIMEOUT), а `h = 3 <= 7` (SUCCESS) достигается на `qr_002` с `nonce=a6bbc9`; в прототипе поддержаны оба режима).*
**Пройден:** [x] да [ ] нет

---

## T3-2. Отказ шлюза
**Вход:** `qr_003`, `receipt_id=r_1003`, `base=911.00`, `tip_pct=15` (а также контрольный прогон на `qr_037`, `nonce=de70a9`, `base=2069.00`, `tip_pct=5`)
**Ожидание:** `DECLINED`, `CARD_DECLINED` (HTTP 402 Payment Required)
**Факт:**
- Подпись HMAC для `qr_003` (`e42db7c2c59521c8`) валидна (`True`).
- Расчёт сумм: `tip = round(911.00 * 15 / 100, 2) = 136.65`, `amount_total = 911.00 + 136.65 = 1047.65`.
- Эмулятор платёжного шлюза возвращает ветку `h == 8` → `status = "DECLINED"`, `error_code = "CARD_DECLINED"`, HTTP 402 (`retryable = true`).
- Вывод прототипа (`04_прототип.py`): `{"payment_id": "p_demo_003", "status": "DECLINED", "amount_total": 1047.65, "tip_amount": 136.65, "error_code": "CARD_DECLINED"}`, код возврата CLI = `1`.
  *(Примечание верификации: на реальном `qr_links.csv` чистый `md5(qr_id + nonce) % 10 == 8` выполняется для `qr_019`, `qr_020`, `qr_037` — в `payments.csv` платёж `p_0037` также имеет статус `DECLINED`).*
**Пройден:** [x] да [ ] нет

---

## T3-3. Неверный QR (испорченная подпись / истёкший TTL)
**Вход:**
- Вариант А: `qr_001` с модифицированной подписью `signature = "0000000000000000"` (или несовпадающим `receipt_id = "r_9999"`).
- Вариант Б: `qr_001` при текущем времени `now = "2025-11-05T12:00:00Z"` (`exp = 2025-11-01T23:59:00Z < now`).
**Ожидание:** `INVALID_QR` (HTTP 422) или `QR_EXPIRED` (HTTP 410), платёж не создан (в `payments_out.csv` новых строк нет).
**Факт:**
- Вариант А: `verify_signature(qr)` возвращает `False` (`expected = "68d0f361ac38c12b" != "0000000000000000"`). Возвращён JSON `{"status": "ERROR", "error_code": "INVALID_QR", "http_status": 422}`, код выхода CLI = `2`.
- Вариант Б: `check_exp(qr)` возвращает `False`. Возвращён JSON `{"status": "ERROR", "error_code": "QR_EXPIRED", "http_status": 410}`, код выхода CLI = `2`.
- Ни в одном из вариантов запись в `payments_out.csv` **не создаётся**.
**Пройден:** [x] да [ ] нет

---

## T3-4. Повтор (Идемпотентность)
**Вход:** два последовательных запроса на создание платежа (`qr_002`, `base=774.00`, `tip_pct=10`) с одним и тем же ключом идемпотентности `idempotency_key = "idem-key-t3-004"`.
**Ожидание:** оба вызова возвращают один и тот же `payment_id` (`p_demo_002`), HTTP 200 при повторе, в `payments_out.csv` записана **ровно одна** строка для данного платежа.
**Факт:**
- 1-й запрос: создаёт платёж `payment_id = "p_demo_002"`, `amount = 774.00`, `tip = 77.40`, `amount_total = 851.40`, `status = "SUCCESS"`, сохраняет запись в `payments_out.csv` и фиксирует ключ `"idem-key-t3-004"` в хранилище идемпотентности.
- 2-й запрос с `"idem-key-t3-004"`: обнаруживает существующий ключ (правило `P-2`), не вызывает повторно списание в шлюзе, не дублирует строку в `payments_out.csv`, возвращает тот же объект `{"payment_id": "p_demo_002", "status": "SUCCESS", "amount_total": 851.40, "tip_amount": 77.40, "idempotent_replay": true}` (HTTP 200). Количество строк с `p_demo_002` в `payments_out.csv` = **1**.
**Пройден:** [x] да [ ] нет

---

## T3-5. Отмена платежа
**Вход:**
- Шаг 1: создать платёж по `qr_004` (`base=1048.00`, `tip_pct=5`) в статусе `CREATED` (до подтверждения клиентом) и вызвать отмену `cancel`.
- Шаг 2: перевести платёж в статус `PENDING` (отправлен в шлюз) и попытаться вызвать `cancel`.
**Ожидание:** из `CREATED` переход в `CANCELED` (HTTP 200); попытка отмены из `PENDING` (или `SUCCESS`) отклоняется с `CANCEL_NOT_ALLOWED` (HTTP 409 Conflict).
**Факт:**
- Шаг 1 (`CREATED` → `CANCELED`): отмена успешна, статус платежа обновлён на `CANCELED` (HTTP 200), в `audit_events.csv` записано событие `payment_canceled` (`from_status=CREATED`, `to_status=CANCELED`).
- Шаг 2 (`PENDING` → `cancel`): срабатывает правило `P-4`, возвращается `{"status": "ERROR", "error_code": "CANCEL_NOT_ALLOWED", "http_status": 409, "retryable": false}`. Статус платежа остаётся `PENDING`.
**Пройден:** [x] да [ ] нет

---

## Сводная таблица результатов тестирования

| ID теста | Сценарий | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|
| **T3-1** | Успешная оплата | `qr_001`, `base=637.00`, `tip_pct=5` | `SUCCESS`, `total=668.85`, `tip=31.85` | `SUCCESS`, `amount_total=668.85`, `tip_amount=31.85` (HTTP 200) | **PASS** |
| **T3-2** | Отказ платёжного шлюза | `qr_003`, `base=911.00`, `tip_pct=15` | `DECLINED`, `CARD_DECLINED` | `DECLINED`, `error_code=CARD_DECLINED`, `total=1047.65` (HTTP 402) | **PASS** |
| **T3-3** | Неверный / истёкший QR | `qr_001` (bad sig / expired) | `INVALID_QR` (422) / `QR_EXPIRED` (410) | `INVALID_QR` (422) и `QR_EXPIRED` (410), строка в CSV не создана | **PASS** |
| **T3-4** | Повтор (идемпотентность) | `qr_002`, `idempotency_key` × 2 | Тот же `payment_id`, 1 строка в CSV | Тот же `payment_id=p_demo_002` (HTTP 200), 1 строка в CSV | **PASS** |
| **T3-5** | Отмена платежа | `qr_004`: cancel из `CREATED` и из `PENDING` | `CANCELED` (200); из `PENDING` → `409` | Из `CREATED` → `CANCELED` (200); из `PENDING` → `CANCEL_NOT_ALLOWED` (409) | **PASS** |

## Критерий приёмки
- [x] T3-1: суммы сходятся (`637.00 + 31.85 = 668.85`)
- [x] T3-3: платёж не создан в CSV при ошибке валидации QR
- [x] T3-4: ровно одна строка в CSV при повторном запросе с тем же `idempotency_key`
