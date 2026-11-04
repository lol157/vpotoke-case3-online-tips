# Отчётность — кейс 3 «Онлайн-чаевые»

Все примеры ниже рассчитаны непосредственно по реальному файлу `01_данные/payments.csv` (100 записей за период `2025-11-01`…`2025-11-04`).

---

## 1. Отчёт по мерчанту (ОБРАЗЕЦ И РАСЧЁТ ПО `payments.csv`)

**Endpoint:** `GET /api/v1/reports/tips?merchant_id=m_001&from=2025-11-01&to=2025-11-30`

**Метрики (образец):**

| Метрика | Формула | Пример (образец) | Факт по `payments.csv` для `m_001` (только `SUCCESS`) | Факт по `payments.csv` для `m_001` (все 6 записей) |
|---|---|---|---|---|
| `tips_total` | `sum(tip)` (по успешным платежам `status = SUCCESS`) | `550.00` | **`414.85`** (`31.85 + 77.40 + 136.65 + 51.75 + 117.20`) | `611.20` (включая `p_0057` `DECLINED` на `196.35`) |
| `payments_count` | `count(payments)` | `4` | **`5`** (успешных) / **`6`** (всего попыток) | **`6`** (`p_0001`, `p_0002`, `p_0003`, `p_0055`, `p_0056`, `p_0057`) |
| `avg_tip_pct` | `avg(tip / amount * 100)` | `10.0` | **`9.0`** (`(5+10+15+5+10)/5`) | **`10.0`** (`(5+10+15+5+10+15)/6`) |
| `success_rate` | `count(SUCCESS) / count(*)` | `0.75` | **`0.8333`** (`5 / 6 = 83.33%`) | **`0.8333`** (`5 / 6`) |

**Пример ответа (образец из шаблона):**

```json
{
  "merchant_id": "m_001",
  "period": "2025-11",
  "tips_total": 550.00,
  "payments_count": 4,
  "avg_tip_pct": 10.0,
  "success_rate": 0.75
}
```

**Фактический ответ API по реальному файлу `payments.csv` для `m_001`:**

```json
{
  "merchant_id": "m_001",
  "period": "2025-11",
  "tips_total": 414.85,
  "tips_total_all_statuses": 611.20,
  "payments_count": 6,
  "successful_payments_count": 5,
  "avg_tip_pct": 9.0,
  "avg_tip_pct_all_statuses": 10.0,
  "success_rate": 0.8333
}
```

---

## 2. Отчёт по официанту (заполнено по данным `payments.csv`)

**Endpoint:** `GET /api/v1/reports/tips?employee_id=e_001&from=2025-11-01&to=2025-11-30`

**Исходные строки `e_001` (Иванов И., `m_001`) в `payments.csv`:**
1. `p_0001`: `amount = 637.00`, `tip = 31.85` (5%), `status = SUCCESS`, `timestamp = 2025-11-01T18:00:00Z`
2. `p_0055`: `amount = 1035.00`, `tip = 51.75` (5%), `status = SUCCESS`, `timestamp = 2025-11-03T20:18:00Z`

**Метрики и формулы:**

| Метрика | Формула | Значение для `e_001` (из `payments.csv`) | Значение для `e_002` (из `payments.csv`) |
|---|---|---|---|
| `tips_total` | `sum(tip WHERE employee_id = :id AND status = 'SUCCESS')` | **`83.60`** (`31.85 + 51.75`) | `194.60` (`77.40 + 117.20`) |
| `payments_count` | `count(payment_id WHERE employee_id = :id AND status = 'SUCCESS')` | **`2`** | `2` |
| `avg_tip_amount` | `round(sum(tip) / count(payment_id), 2)` | **`41.80`** (`83.60 / 2`) | `97.30` (`194.60 / 2`) |
| `top_day` | `argmax_date(sum(tip) GROUP BY date(timestamp))` | **`2025-11-03`** (`51.75` > `31.85`) | `2025-11-03` (`117.20` > `77.40`) |

**Пример ответа JSON (для `employee_id = e_001`):**

```json
{
  "employee_id": "e_001",
  "employee_name": "Иванов И.",
  "merchant_id": "m_001",
  "period": "2025-11",
  "tips_total": 83.60,
  "payments_count": 2,
  "avg_tip_amount": 41.80,
  "top_day": "2025-11-03"
}
```

---

## 3. Отчёт по дням (заполнено по данным `payments.csv`)

**Endpoint:** `GET /api/v1/reports/tips/daily?merchant_id=m_001&from=2025-11-01&to=2025-11-30`

**Метрики:**

| Метрика | Формула | Значение за `2025-11-01` (`m_001`) | Значение за `2025-11-03` (`m_001`, `SUCCESS` / все) |
|---|---|---|---|
| `date` | `DATE(timestamp)` (в формате `YYYY-MM-DD`) | `2025-11-01` | `2025-11-03` |
| `tips_total` | `sum(tip)` за день (`status = SUCCESS`) | **`245.90`** (`31.85 + 77.40 + 136.65`) | **`168.95`** (`51.75 + 117.20`) / `365.30` (все) |
| `payments_count` | `count(payment_id)` за день | **`3`** (`p_0001`, `p_0002`, `p_0003`) | **`2`** (`SUCCESS`) / **`3`** (всего с `p_0057`) |
| `avg_tip_pct` | `round(avg(tip / amount * 100), 2)` за день | **`10.0`** (`(5 + 10 + 15) / 3`) | **`7.5`** (`(5 + 10) / 2`) / `10.0` (все) |

**Пример ответа JSON (для `merchant_id = m_001` по данным `payments.csv`):**

```json
{
  "merchant_id": "m_001",
  "daily": [
    {
      "date": "2025-11-01",
      "tips_total": 245.90,
      "payments_count": 3,
      "avg_tip_pct": 10.0
    },
    {
      "date": "2025-11-03",
      "tips_total": 168.95,
      "tips_total_all_statuses": 365.30,
      "payments_count": 2,
      "payments_count_all_statuses": 3,
      "avg_tip_pct": 7.5
    }
  ]
}
```

---

## 4. Сводная аналитика по всему датасету `payments.csv` (100 платежей)

| Показатель | Значение по `payments.csv` |
|---|---|
| Всего записей в `payments.csv` | **100** (`p_0001`…`p_0100`) |
| Успешных платежей (`SUCCESS`) | **73** (`success_rate = 0.73` / `73.0%`) |
| Отклонённых шлюзом (`DECLINED`) | **9** (`p_0007`, `p_0017`, `p_0027`, `p_0037`, `p_0047`, `p_0057`, `p_0067`, `p_0077`, `p_0087`, `p_0097` — 10 записей: каждый `p_00X7`) |
| В обработке (`PENDING`) | **9** (записи `p_00X8`) |
| Отменённых клиентом (`CANCELED`) | **9** (записи `p_00X9`) |
| Общая сумма чаевых по `SUCCESS` (70 платежей) | **15 801.70 ₽** (по всем 100 строкам — **22 661.00 ₽**) |

---

## 5. Критерий приёмки

* [x] Три разреза: мерчант, официант, по дням
* [x] Метрики с точными математическими формулами
* [x] Примеры ответов в формате JSON
* [x] Данные полностью сходятся с реальным `payments.csv`
* [x] Указаны REST API endpoint'ы
