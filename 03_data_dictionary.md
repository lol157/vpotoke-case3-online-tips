# Data dictionary — кейс 3 «Онлайн-чаевые»

## Как заполнять

Четыре файла: `merchants.csv` (4 колонки), `employees.csv` (4 колонки), `payments.csv` (7 колонок), `qr_links.csv` (7 колонок) — всего **22 колонки**.
Ниже сохранены образцы и приведено полное описание всех 22 полей всех 4 таблиц с реальными примерами из CSV и кодами ошибок.

## Образец merchants (не трогать)

| Файл | Поле | Тип | Обяз. | Ограничение | Пример | Код ошибки |
|---|---|---|---|---|---|---|
| merchants | merchant\_id | string | да | m\_NNN | m\_001 | — |
| merchants | name | string | да | 1–100 символов | Вкус-Сервис Тверская | — |
| merchants | status | enum | да | ACTIVE/BLOCKED/PENDING | ACTIVE | MERCHANT\_BLOCKED |
| merchants | description | string | нет | 0–200 | Ресторан сети, Тверская | — |

## Образец payments (не трогать)

| Файл | Поле | Тип | Обяз. | Ограничение | Пример | Код ошибки |
|---|---|---|---|---|---|---|
| payments | payment\_id | string | да | p\_NNNN | p\_0001 | — |
| payments | amount | decimal | да | > 0, ≤ 1 000 000 | 637.00 | AMOUNT\_OUT\_OF\_RANGE |
| payments | tip | decimal | да | ≥ 0, ≤ amount × 0.5 | 31.85 | TIP\_OUT\_OF\_RANGE |
| payments | status | enum | да | CREATED/PENDING/SUCCESS/DECLINED/CANCELED | SUCCESS | — |

### Полная таблица — payments (все 7 колонок файла `payments.csv`)

| Файл | Поле | Тип | Обяз. | Ограничение | Пример (из CSV) | Код ошибки |
|---|---|---|---|---|---|---|
| payments | `payment_id` | string | да | PK, формат `^p_[0-9]{4,}$` | `p_0001` | `—` |
| payments | `merchant_id` | string | да | FK → `merchants.merchant_id`, `^m_[0-9]{3}$`, статус `ACTIVE` | `m_001` | `MERCHANT_BLOCKED` |
| payments | `employee_id` | string | да | FK → `employees.employee_id`, `^e_[0-9]{3}$` | `e_001` | `INVALID_QR` |
| payments | `amount` | decimal(10,2) | да | `> 0`, `<= 1 000 000.00` | `637.00` | `AMOUNT_OUT_OF_RANGE` |
| payments | `tip` | decimal(10,2) | да | `>= 0`, `<= amount * 0.5` (`tip_pct` 0..50%) | `31.85` | `TIP_OUT_OF_RANGE` |
| payments | `status` | enum | да | `CREATED` / `PENDING` / `SUCCESS` / `DECLINED` / `CANCELED` | `SUCCESS` | `CANCEL_NOT_ALLOWED` |
| payments | `timestamp` | datetime (ISO 8601) | да | формат `YYYY-MM-DDTHH:MM:SSZ` (UTC) | `2025-11-01T18:00:00Z` | `—` |

## Твоя таблица — employees (все 4 колонки файла `employees.csv`)

| Поле | Тип | Обяз. | Ограничение | Пример (из CSV) | Код ошибки |
|---|---|---|---|---|---|
| `employee_id` | string | да | PK, формат `^e_[0-9]{3}$` (`e_001`…`e_060`), уникальный | `e_001` | `NOT_FOUND` |
| `merchant_id` | string | да | FK → `merchants.merchant_id`, формат `^m_[0-9]{3}$` | `m_001` | `MERCHANT_BLOCKED` |
| `name` | string | да | 1–100 символов (ФИО / имя и инициалы официанта) | `Иванов И.` | `VALIDATION_ERROR` |
| `payment_details` | string | да | Строго маска реквизитов выплат `^\*{4}[0-9]{4}$` (`****NNNN`), полный PAN не хранится | `****1001` | `INVALID_PAYMENT_DETAILS` |

## Твоя таблица — qr\_links (все 7 колонок файла `qr_links.csv`)

| Поле | Тип | Обяз. | Ограничение | Пример (из CSV) | Код ошибки |
|---|---|---|---|---|---|
| `qr_id` | string | да | PK, формат `^qr_[0-9]{3}$` (`qr_001`…`qr_100`), уникальный | `qr_001` | `INVALID_QR` |
| `merchant_id` | string | да | FK → `merchants.merchant_id`, формат `^m_[0-9]{3}$`, `status = ACTIVE` | `m_001` | `MERCHANT_BLOCKED` |
| `employee_id` | string | да | FK → `employees.employee_id`, формат `^e_[0-9]{3}$`, принадлежит `merchant_id` | `e_001` | `INVALID_QR` |
| `receipt_id` | string | да | Формат `^r_[0-9]{4}$` (`r_1001`…`r_1100`), уникален в рамках мерчанта | `r_1001` | `RECEIPT_MISMATCH` |
| `nonce` | string | да | Формат `^[a-f0-9]{6}$` (6 hex-символов), криптостойкий одноразовый токен | `c82561` | `QR_USED` |
| `exp` | datetime (ISO 8601) | да | Формат `YYYY-MM-DDTHH:MM:SSZ`, `exp >= now` (TTL = 24 ч от генерации) | `2025-11-01T23:59:00Z` | `QR_EXPIRED` |
| `signature` | string | да | Формат `^[a-f0-9]{16}$` (первые 16 hex от `HMAC-SHA256(SECRET, payload)`) | `68d0f361ac38c12b` | `INVALID_QR` |

## Критерий приёмки

- [x] Все 4 файла описаны (22 колонки: 4 + 4 + 7 + 7)
- [x] Для каждого поля указан тип и ограничение
- [x] Для полей с валидацией — код ошибки из `08_errors.md`
- [x] Пример взят из реального CSV (`m_001`, `e_001`, `p_0001`, `qr_001`)
- [x] `payment_details` — только маска (`****NNNN`, пример `****1001`)
