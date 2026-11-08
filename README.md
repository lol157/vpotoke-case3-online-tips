# Кейс №3 «Онлайн-чаевые: платформа для ресторанов» (Сеть «Вкус-Сервис»)

Полное решение кейса №3 чемпионата «ВПОТОКЕ» (репозиторий: https://github.com/lol157/vpotoke-case3-online-tips, ветка [`team_1_case_3`](https://github.com/lol157/vpotoke-case3-online-tips/tree/team_1_case_3)).

---

## Структура репозитория

| Файл / Директория | Описание |
|---|---|
| [`01_данные/`](01_данные/) | Неизменённые исходные CSV-файлы (`merchants.csv`, `employees.csv`, `payments.csv`, `qr_links.csv`) |
| [`02_roles.md`](02_roles.md) (`02_roles(1).md`) | Описание 4 ролей, матрица RBAC (8×4), процессы регистрации мерчанта и сотрудника |
| [`02_правила.md`](02_правила.md) | 6 правил проверки QR (`Q-1`…`Q-6`) и 4 правила платежа (`P-1`…`P-4`) |
| [`03_data_dictionary.md`](03_data_dictionary.md) | Словарь данных (все 22 колонки 4 CSV-файлов) |
| [`03_тесты.md`](03_тесты.md) (`10_tests.md`) | 5 тест-сценариев (`T3-1`…`T3-5`) с заполненным разделом «Факт» |
| [`04_requirements.md`](04_requirements.md) | Функциональные (`FR-1`…`FR-10`), нефункциональные (`NFR-1`…`NFR-6`) требования и пользовательские сценарии |
| [`04_прототип.py`](04_прототип.py) | Консольный прототип (CLI) строго по шаблону кейса |
| [`05_api_schemas.yaml`](05_api_schemas.yaml) | Спецификация OpenAPI 3.0.3 |
| [`05_презентация.md`](05_презентация.md) | Текст и структура презентации (8 слайдов) |
| [`05_Презентация_Кейс3_Онлайн_Чаевые.pdf`](05_Презентация_Кейс3_Онлайн_Чаевые.pdf) | Презентация в формате PDF (8 слайдов) |
| [`06_qr_and_tip_dialog.md`](06_qr_and_tip_dialog.md) | Payload QR, подпись `HMAC-SHA256`, генерация ссылки и 4 экрана диалога |
| [`06_приложение.md`](06_приложение.md) | Приложение к презентации (разделы A–F: схемы, таблицы, тесты, журнал промптов ИИ, матрица вклада) |
| [`06_Приложение_Кейс3_Онлайн_Чаевые.pdf`](06_Приложение_Кейс3_Онлайн_Чаевые.pdf) | Приложение в формате PDF |
| [`07_payment_emulator_template.md`](07_payment_emulator_template.md) | Механизм эмуляции платежа: 5 состояний, матрица переходов, формулы, расчёты `qr_001` и `qr_003` |
| [`08_errors.md`](08_errors.md) (`08_ER.md`) | ER-модель данных (6 сущностей, PK/FK, связи `1:N`) и справочник кодов ошибок |
| [`09_reports.md`](09_reports.md) | Отчётность в 3 разрезах (по мерчанту, по официанту, по дням) |
| [`11_ИБ.md`](11_ИБ.md) | Информационная безопасность: угрозы `U-1`…`U-6`, меры защиты, RBAC, аудит, маскирование |
| [`test_inputs/`](test_inputs/) | Входные JSON-файлы для проверки всех 5 тест-сценариев (`T3-1`…`T3-5`) |
| [`diagrams/`](diagrams/) | Схемы в форматах `.png` и `.drawio` |

---

## Запуск прототипа и проверка 5 тест-сценариев

```bash
# T3-1. Успех (qr_001, base=637.00, tip_pct=5 -> SUCCESS, total=668.85, tip=31.85)
python 04_прототип.py test_inputs/t3_1_success.json

# T3-2. Отказ шлюза (qr_003, base=911.00, tip_pct=15 -> DECLINED, CARD_DECLINED)
python 04_прототип.py test_inputs/t3_2_declined.json

# T3-3. Неверный QR (испорченная подпись -> INVALID_QR, платёж не создаётся)
python 04_прототип.py test_inputs/t3_3_invalid_qr.json

# T3-4. Повтор (тот же idempotency_key дважды -> одна строка в payments_out.csv)
python 04_прототип.py test_inputs/t3_4_idem.json
python 04_прототип.py test_inputs/t3_4_idem.json

# T3-5. Отмена (из CREATED -> CANCELED; из PENDING -> 409 CANCEL_NOT_ALLOWED)
python 04_прототип.py test_inputs/t3_5_create.json
python 04_прототип.py test_inputs/t3_5_cancel.json
python 04_прототип.py test_inputs/t3_5_pending.json
python 04_прототип.py test_inputs/t3_5_cancel_pending.json
```
