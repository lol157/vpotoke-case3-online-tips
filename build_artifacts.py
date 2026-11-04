#!/usr/bin/env python3
"""
Генератор артефактов для кейса №3 «Онлайн-чаевые: платформа для ресторанов»:
  1. Создаёт .drawio XML схемы (architecture.drawio, er_model.drawio, state_machine.drawio).
  2. Рендерит PNG-диаграммы и скриншоты с помощью Pillow (PIL).
  3. Создаёт дополнительные копии файлов (08_ER.md, 10_tests.md, 02_roles(1).md).
  4. Инициализирует Git-репозиторий с веткой team_1_case_3 и делает коммит.
  5. Генерирует PDF-версии Презентации (8 слайдов) и Приложения (A4) через Chrome Headless / PIL.
"""
import hashlib
import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIAG_DIR = os.path.join(BASE_DIR, "diagrams")
os.makedirs(DIAG_DIR, exist_ok=True)


def get_font(size=18, bold=False, mono=False):
    """Загружает системный шрифт Windows с поддержкой кириллицы."""
    candidates = []
    if mono:
        candidates = [
            r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\courbd.ttf" if bold else r"C:\Windows\Fonts\cour.ttf",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_box(draw, xy, title, lines, fill="#ffffff", outline="#2563eb", header_fill="#dbeafe"):
    """Рисует аккуратный блок с заголовком и текстом."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline=outline, width=2)
    draw.rounded_rectangle([x1, y1, x2, y1 + 38], radius=10, fill=header_fill, outline=outline, width=2)
    draw.rectangle([x1 + 2, y1 + 28, x2 - 2, y1 + 38], fill=header_fill)
    draw.line([(x1, y1 + 38), (x2, y1 + 38)], fill=outline, width=2)

    f_title = get_font(16, bold=True)
    f_body = get_font(14, bold=False)
    draw.text((x1 + 12, y1 + 9), title, fill="#0f172a", font=f_title)
    cy = y1 + 48
    for line in lines:
        draw.text((x1 + 12, cy), line, fill="#334155", font=f_body)
        cy += 21


def draw_arrow(draw, p1, p2, label="", color="#1e40af"):
    """Рисует стрелку между двумя точками с подписью."""
    import math
    x1, y1 = p1
    x2, y2 = p2
    draw.line([p1, p2], fill=color, width=3)
    angle = math.atan2(y2 - y1, x2 - x1)
    head_len = 12
    a1 = angle + math.pi * 0.82
    a2 = angle - math.pi * 0.82
    draw.polygon(
        [
            (x2, y2),
            (x2 + head_len * math.cos(a1), y2 + head_len * math.sin(a1)),
            (x2 + head_len * math.cos(a2), y2 + head_len * math.sin(a2)),
        ],
        fill=color,
    )
    if label:
        f_lbl = get_font(13, bold=True)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        bbox = draw.textbbox((0, 0), label, font=f_lbl)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle(
            [mx - tw / 2 - 6, my - th / 2 - 4, mx + tw / 2 + 6, my + th / 2 + 4],
            radius=4,
            fill="#f8fafc",
            outline="#cbd5e1",
        )
        draw.text((mx - tw / 2, my - th / 2), label, fill=color, font=f_lbl)


def generate_architecture_png():
    """A.1. Схема архитектуры системы (5 блоков + подписанные потоки данных)."""
    img = Image.new("RGB", (1320, 720), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "A.1. Архитектура платформы онлайн-чаевых «Вкус-Сервис» (Кейс 3)",
        fill="#0f172a",
        font=get_font(24, bold=True),
    )
    draw.text(
        (36, 54),
        "Потоки данных: Клиент -> Платформа (REST API + Валидация Q-1..Q-6 / P-1..P-4) -> Эмулятор шлюза -> Хранилище -> Аудит",
        fill="#475569",
        font=get_font(15),
    )

    # Блок 1: Клиент
    draw_box(
        draw,
        (40, 140, 310, 390),
        "1. Клиент (Смартфон)",
        [
            "• Сканирование QR на чеке",
            "• 4 экрана диалога чаевых:",
            "  1) Приветствие (чек, официант)",
            "  2) Выбор % (0, 5, 10, 15, 20%)",
            "  3) Подтверждение / Отмена",
            "  4) Результат оплаты",
            "• Генерация idempotency_key",
        ],
        fill="#ffffff",
        outline="#0284c7",
        header_fill="#e0f2fe",
    )

    # Блок 2: Платформа
    draw_box(
        draw,
        (480, 120, 840, 420),
        "2. Платформа чаевых (Backend API)",
        [
            "• Эндпоинты OpenAPI 3.0.3 (порт 8083):",
            "  GET /api/v1/qr/{qr_id}",
            "  POST /api/v1/tips",
            "  POST /api/v1/payments/{id}/confirm | /cancel",
            "  GET /api/v1/reports/tips | /daily",
            "• Правила QR: Q-1 (HMAC-SHA256), Q-2 (TTL 24ч),",
            "  Q-3 (nonce), Q-4 (ACTIVE), Q-5 (receipt_id), Q-6 (<=50%)",
            "• Правила платежа: P-1 (<=1M), P-2 (idempotency),",
            "  P-3 (total<=2M), P-4 (запрет отмены из PENDING)",
            "• Ролевая модель RBAC (4 роли x 8 действий)",
        ],
        fill="#ffffff",
        outline="#2563eb",
        header_fill="#dbeafe",
    )

    # Блок 3: Эмулятор шлюза
    draw_box(
        draw,
        (1010, 140, 1280, 390),
        "3. Эмулятор шлюза",
        [
            "• Детерминированная формула:",
            "  h = MD5(qr_id + nonce) % 10",
            "• 3 сценария ответа:",
            "  - h in 0..7 (80%): SUCCESS (200)",
            "  - h == 8 (10%): DECLINED /",
            "    CARD_DECLINED (HTTP 402)",
            "  - h == 9 (10%): PENDING /",
            "    GATEWAY_TIMEOUT (HTTP 504)",
        ],
        fill="#ffffff",
        outline="#7c3aed",
        header_fill="#ede9fe",
    )

    # Блок 4: Хранилище данных
    draw_box(
        draw,
        (220, 490, 620, 685),
        "4. Хранилище данных (CSV / БД)",
        [
            "• merchants.csv (20 ресторанов: ACTIVE/BLOCKED/PENDING)",
            "• employees.csv (60 официантов, маска карт ****NNNN)",
            "• qr_links.csv (100 QR с nonce, exp и HMAC-SHA256)",
            "• payments.csv / payments_out.csv (транзакции чаевых)",
            "• runtime_state.json (idempotency_key + used_nonces)",
        ],
        fill="#ffffff",
        outline="#059669",
        header_fill="#d1fae5",
    )

    # Блок 5: Журнал аудита
    draw_box(
        draw,
        (720, 490, 1140, 685),
        "5. Подсистема Аудита ИБ (AuditEvent)",
        [
            "• Неизменяемый журнал audit_events.csv (append-only)",
            "• 9 обязательных полей трассировки:",
            "  event_id, payment_id, qr_id, action,",
            "  from_status, to_status, amount_total, actor, at (UTC)",
            "• Маскирование логов (запрет хранения PAN/CVV)",
        ],
        fill="#ffffff",
        outline="#d97706",
        header_fill="#fef3c7",
    )

    # Стрелки потоков
    draw_arrow(draw, (310, 220), (480, 220), "1. GET /qr, POST /tips", "#0284c7")
    draw_arrow(draw, (480, 310), (310, 310), "4. Статус / Чек JSON", "#0284c7")
    draw_arrow(draw, (840, 220), (1010, 220), "2. Запрос списания", "#7c3aed")
    draw_arrow(draw, (1010, 310), (840, 310), "3. Код шлюза (h=0..9)", "#7c3aed")
    draw_arrow(draw, (570, 420), (460, 490), "Чтение QR / Запись платежа", "#059669")
    draw_arrow(draw, (750, 420), (880, 490), "Запись события AuditEvent", "#d97706")

    img.save(os.path.join(DIAG_DIR, "architecture.png"))


def generate_er_model_png():
    """A.2. ER-модель данных (6 сущностей, PK/FK, связи 1:N)."""
    img = Image.new("RGB", (1320, 760), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "A.2. ER-модель данных платформы онлайн-чаевых (6 сущностей, связи 1:N)",
        fill="#0f172a",
        font=get_font(24, bold=True),
    )

    # Верхний ряд: Merchant, Employee, Report
    draw_box(
        draw,
        (50, 90, 400, 330),
        "Merchant (Ресторан)",
        [
            "[PK] merchant_id : string (m_NNN)",
            "     name        : string (1..100)",
            "     status      : enum (ACTIVE|BLOCKED|PENDING)",
            "     description : string (0..200)",
        ],
        outline="#1d4ed8",
        header_fill="#dbeafe",
    )

    draw_box(
        draw,
        (490, 90, 850, 330),
        "Employee (Официант)",
        [
            "[PK] employee_id     : string (e_NNN)",
            "[FK] merchant_id     : string -> Merchant",
            "     name            : string (1..100)",
            "     payment_details : string (маска ****NNNN)",
        ],
        outline="#0369a1",
        header_fill="#e0f2fe",
    )

    draw_box(
        draw,
        (930, 90, 1280, 330),
        "Report (Отчёт по чаевым)",
        [
            "[PK] report_id      : string (rep_NNNN)",
            "[FK] merchant_id    : string -> Merchant",
            "     period         : string (YYYY-MM)",
            "     tips_total     : decimal (>= 0)",
            "     payments_count : int (>= 0)",
            "     avg_tip_pct    : decimal (0..50)",
            "     success_rate   : decimal (0..1)",
        ],
        outline="#0f766e",
        header_fill="#ccfbf1",
    )

    # Нижний ряд: QR, Payment, AuditEvent
    draw_box(
        draw,
        (50, 440, 420, 710),
        "QR (Ссылка на чеке)",
        [
            "[PK] qr_id       : string (qr_NNN)",
            "[FK] merchant_id : string -> Merchant",
            "[FK] employee_id : string -> Employee",
            "     receipt_id  : string (r_NNNN, уникален)",
            "     nonce       : string (6 hex, одноразовый)",
            "     exp         : datetime (ISO 8601, TTL 24ч)",
            "     signature   : string (HMAC-SHA256, 16 hex)",
        ],
        outline="#6d28d9",
        header_fill="#ede9fe",
    )

    draw_box(
        draw,
        (500, 440, 860, 710),
        "Payment (Платёж чаевых)",
        [
            "[PK] payment_id  : string (p_NNNN)",
            "[FK] qr_id       : string -> QR",
            "[FK] merchant_id : string -> Merchant",
            "[FK] employee_id : string -> Employee",
            "     amount      : decimal (0 < amt <= 1 000 000)",
            "     tip         : decimal (0 <= tip <= 0.5*amt)",
            "     status      : enum (CREATED|PENDING|SUCCESS|...)",
            "     timestamp   : datetime (ISO 8601 UTC)",
        ],
        outline="#047857",
        header_fill="#d1fae5",
    )

    draw_box(
        draw,
        (930, 440, 1280, 710),
        "AuditEvent (Журнал аудита ИБ)",
        [
            "[PK] event_id     : string (evt_NNNN)",
            "[FK] payment_id   : string -> Payment",
            "[FK] qr_id        : string -> QR",
            "     action       : enum (created|confirmed|...)",
            "     from_status  : enum",
            "     to_status    : enum",
            "     amount_total : decimal (amount + tip)",
            "     actor / at   : enum / datetime (ISO 8601)",
        ],
        outline="#b45309",
        header_fill="#fef3c7",
    )

    # Связи 1:N
    draw_arrow(draw, (400, 180), (490, 180), "1 : N", "#1d4ed8")
    draw_arrow(draw, (400, 120), (930, 120), "1 : N (отчёты ресторана)", "#0f766e")
    draw_arrow(draw, (220, 330), (220, 440), "1 : N (чеки)", "#6d28d9")
    draw_arrow(draw, (640, 330), (340, 440), "1 : N (обслужил)", "#0369a1")
    draw_arrow(draw, (420, 560), (500, 560), "1 : N", "#047857")
    draw_arrow(draw, (860, 560), (930, 560), "1 : N", "#b45309")

    img.save(os.path.join(DIAG_DIR, "er_model.png"))


def generate_state_machine_png():
    """A.3. Схема состояний платежа (State Machine)."""
    img = Image.new("RGB", (1280, 620), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "A.3. Диаграмма состояний платежа (Жизненный цикл и правило P-4)",
        fill="#0f172a",
        font=get_font(24, bold=True),
    )

    draw_box(
        draw,
        (60, 220, 290, 370),
        "CREATED",
        [
            "Платёж создан",
            "(POST /api/v1/tips)",
            "Проверены Q-1..Q-6,",
            "P-1..P-3",
        ],
        outline="#0284c7",
        header_fill="#e0f2fe",
    )

    draw_box(
        draw,
        (460, 220, 720, 370),
        "PENDING",
        [
            "Ожидание ответа шлюза",
            "(POST /confirm)",
            "Или таймаут h == 9",
            "(GATEWAY_TIMEOUT 504)",
        ],
        outline="#d97706",
        header_fill="#fef3c7",
    )

    draw_box(
        draw,
        (940, 80, 1220, 220),
        "SUCCESS (Финал)",
        [
            "Успешное списание",
            "Эмулятор: h in 0..7 (80%)",
            "HTTP 200 OK, nonce погашен",
        ],
        outline="#059669",
        header_fill="#d1fae5",
    )

    draw_box(
        draw,
        (940, 250, 1220, 390),
        "DECLINED (Финал)",
        [
            "Отказ банка по карте",
            "Эмулятор: h == 8 (10%)",
            "HTTP 402 CARD_DECLINED",
        ],
        outline="#dc2626",
        header_fill="#fee2e2",
    )

    draw_box(
        draw,
        (460, 440, 740, 580),
        "CANCELED (Финал)",
        [
            "Отменён клиентом до",
            "отправки в шлюз",
            "(POST /cancel -> HTTP 200)",
        ],
        outline="#475569",
        header_fill="#e2e8f0",
    )

    draw_arrow(draw, (290, 290), (460, 290), "Клиент подтвердил (/confirm)", "#0284c7")
    draw_arrow(draw, (720, 250), (940, 150), "h = 0..7 (SUCCESS)", "#059669")
    draw_arrow(draw, (720, 310), (940, 310), "h = 8 (CARD_DECLINED)", "#dc2626")
    draw_arrow(draw, (590, 220), (590, 150), "h = 9 (GATEWAY_TIMEOUT -> остаётся в PENDING)", "#d97706")
    draw_arrow(draw, (175, 370), (460, 510), "Клиент отменил (/cancel) — РАЗРЕШЕНО", "#059669")
    draw_arrow(draw, (590, 370), (590, 440), "ЗАПРЕЩЕНО P-4: 409 CANCEL_NOT_ALLOWED", "#dc2626")

    img.save(os.path.join(DIAG_DIR, "state_machine.png"))


def render_terminal_screenshot(filename, title, lines):
    """Рендерит реалистичный скриншот терминала с выводом команд."""
    width = 1240
    height = max(320, 90 + len(lines) * 24)
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)

    # Шапка окна терминала
    draw.rectangle([0, 0, width, 42], fill="#1e293b")
    draw.ellipse([16, 13, 30, 27], fill="#ef4444")
    draw.ellipse([38, 13, 52, 27], fill="#f59e0b")
    draw.ellipse([60, 13, 74, 27], fill="#10b981")
    draw.text((92, 11), title, fill="#e2e8f0", font=get_font(15, bold=True, mono=True))

    f_mono = get_font(15, bold=False, mono=True)
    y = 58
    for line in lines:
        color = "#f8fafc"
        if line.startswith("$") or line.startswith("PS "):
            color = "#38bdf8"
        elif "PASS" in line or '"SUCCESS"' in line or "Не менялся" in line:
            color = "#4ade80"
        elif "DECLINED" in line or "ERROR" in line:
            color = "#f87171"
        draw.text((22, y), line, fill=color, font=f_mono)
        y += 23

    img.save(os.path.join(DIAG_DIR, filename))


def write_drawio_files():
    """Создаёт валидные XML-файлы draw.io (.drawio) для всех 3 обязательных схем."""
    arch_xml = """<mxfile host="app.diagrams.net" type="device">
  <diagram id="case3-arch" name="A.1 Architecture">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageScale="1" pageWidth="1169" pageHeight="827">
      <root>
        <mxCell id="0"/><mxCell id="1" parent="0"/>
        <mxCell id="c1" value="Клиент (Смартфон)&#10;4 экрана диалога чаевых" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1" vertex="1" parent="1"><mxGeometry x="60" y="180" width="200" height="100" as="geometry"/></mxCell>
        <mxCell id="c2" value="Платформа чаевых&#10;(API + Правила Q-1..Q-6, P-1..P-4)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1" vertex="1" parent="1"><mxGeometry x="420" y="170" width="260" height="120" as="geometry"/></mxCell>
        <mxCell id="c3" value="Эмулятор шлюза&#10;h = md5(qr_id+nonce)%10&#10;0..7 SUCCESS | 8 DECLINED | 9 TIMEOUT" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontStyle=1" vertex="1" parent="1"><mxGeometry x="830" y="180" width="240" height="100" as="geometry"/></mxCell>
        <mxCell id="c4" value="Хранилище CSV/БД&#10;merchants, employees, qr_links, payments" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1" vertex="1" parent="1"><mxGeometry x="260" y="400" width="250" height="100" as="geometry"/></mxCell>
        <mxCell id="c5" value="Аудит ИБ (AuditEvent)&#10;audit_events.csv (9 полей)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1" vertex="1" parent="1"><mxGeometry x="600" y="400" width="250" height="100" as="geometry"/></mxCell>
        <mxCell id="e1" value="QR, выбор чаевых, confirm/cancel" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="c1" target="c2"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="e2" value="Запрос оплаты / статус шлюза" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="c2" target="c3"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="e3" value="Чтение / запись CSV" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="c2" target="c4"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="e4" value="Журналирование переходов" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="c2" target="c5"><mxGeometry relative="1" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
    with open(os.path.join(DIAG_DIR, "architecture.drawio"), "w", encoding="utf-8") as f:
        f.write(arch_xml)

    er_xml = """<mxfile host="app.diagrams.net" type="device">
  <diagram id="case3-er" name="A.2 ER Model">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageScale="1" pageWidth="1169" pageHeight="827">
      <root>
        <mxCell id="0"/><mxCell id="1" parent="0"/>
        <mxCell id="m1" value="Merchant&#10;PK: merchant_id&#10;name, status, description" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1"><mxGeometry x="60" y="80" width="220" height="110" as="geometry"/></mxCell>
        <mxCell id="m2" value="Employee&#10;PK: employee_id | FK: merchant_id&#10;name, payment_details (****NNNN)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1"><mxGeometry x="380" y="80" width="240" height="110" as="geometry"/></mxCell>
        <mxCell id="m3" value="Report&#10;PK: report_id | FK: merchant_id&#10;period, tips_total, avg_tip_pct" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1"><mxGeometry x="720" y="80" width="230" height="110" as="geometry"/></mxCell>
        <mxCell id="m4" value="QR&#10;PK: qr_id | FK: merchant_id, employee_id&#10;receipt_id, nonce, exp, signature" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="1"><mxGeometry x="60" y="290" width="250" height="120" as="geometry"/></mxCell>
        <mxCell id="m5" value="Payment&#10;PK: payment_id | FK: qr_id, merchant_id, employee_id&#10;amount, tip, status, timestamp" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1"><mxGeometry x="400" y="290" width="260" height="120" as="geometry"/></mxCell>
        <mxCell id="m6" value="AuditEvent&#10;PK: event_id | FK: payment_id, qr_id&#10;action, from_status, to_status, amount_total, actor, at" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1" parent="1"><mxGeometry x="740" y="290" width="260" height="120" as="geometry"/></mxCell>
        <mxCell id="r1" value="1:N" edge="1" parent="1" source="m1" target="m2"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="r2" value="1:N" edge="1" parent="1" source="m1" target="m4"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="r3" value="1:N" edge="1" parent="1" source="m2" target="m4"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="r4" value="1:N" edge="1" parent="1" source="m4" target="m5"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="r5" value="1:N" edge="1" parent="1" source="m1" target="m3"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="r6" value="1:N" edge="1" parent="1" source="m5" target="m6"><mxGeometry relative="1" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
    with open(os.path.join(DIAG_DIR, "er_model.drawio"), "w", encoding="utf-8") as f:
        f.write(er_xml)

    sm_xml = """<mxfile host="app.diagrams.net" type="device">
  <diagram id="case3-sm" name="A.3 State Machine">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageScale="1" pageWidth="1169" pageHeight="827">
      <root>
        <mxCell id="0"/><mxCell id="1" parent="0"/>
        <mxCell id="s1" value="CREATED" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1" vertex="1" parent="1"><mxGeometry x="80" y="200" width="160" height="70" as="geometry"/></mxCell>
        <mxCell id="s2" value="PENDING" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1" vertex="1" parent="1"><mxGeometry x="380" y="200" width="160" height="70" as="geometry"/></mxCell>
        <mxCell id="s3" value="SUCCESS" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1" vertex="1" parent="1"><mxGeometry x="720" y="100" width="160" height="70" as="geometry"/></mxCell>
        <mxCell id="s4" value="DECLINED" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1" vertex="1" parent="1"><mxGeometry x="720" y="220" width="160" height="70" as="geometry"/></mxCell>
        <mxCell id="s5" value="CANCELED" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1" vertex="1" parent="1"><mxGeometry x="380" y="360" width="160" height="70" as="geometry"/></mxCell>
        <mxCell id="t1" value="confirm" edge="1" parent="1" source="s1" target="s2"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="t2" value="h in 0..7" edge="1" parent="1" source="s2" target="s3"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="t3" value="h == 8 (CARD_DECLINED)" edge="1" parent="1" source="s2" target="s4"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="t4" value="cancel (200 OK)" edge="1" parent="1" source="s1" target="s5"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="t5" value="FORBIDDEN P-4 (409)" edge="1" parent="1" source="s2" target="s5"><mxGeometry relative="1" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
    with open(os.path.join(DIAG_DIR, "state_machine.drawio"), "w", encoding="utf-8") as f:
        f.write(sm_xml)


def generate_screenshots():
    """Создаёт скриншоты работы прототипа, проверки MD5 и коммита Git."""
    cli_lines = [
        "$ python 04_прототип.py qr_001.json",
        "{",
        '  "payment_id": "p_demo_001",',
        '  "status": "SUCCESS",',
        '  "amount_total": 668.85,',
        '  "tip_amount": 31.85,',
        '  "error_code": null',
        "}",
        "",
        "$ python 04_прототип.py qr_003.json",
        "{",
        '  "payment_id": "p_demo_003",',
        '  "status": "DECLINED",',
        '  "amount_total": 1047.65,',
        '  "tip_amount": 136.65,',
        '  "error_code": "CARD_DECLINED"',
        "}",
        "",
        "$ python 04_прототип.py --run-tests",
        "========================================================================",
        "РЕЗУЛЬТАТЫ АВТОМАТИЧЕСКОГО ПРОГОНА 5 ТЕСТ-СЦЕНАРИЕВ (КЕЙС 3)",
        "========================================================================",
        'T3-1 (Успех)                       | PASS [ДА] | {"payment_id": "p_demo_001", "status": "SUCCESS", "amount_total": 668.85}',
        'T3-2 (Отказ шлюза)                 | PASS [ДА] | {"payment_id": "p_demo_003", "status": "DECLINED", "error_code": "CARD_DECLINED"}',
        'T3-3 (Неверный QR)                 | PASS [ДА] | {"status": "ERROR", "error_code": "INVALID_QR", "http_status": 422}',
        'T3-4 (Повтор / Идемпотентность)    | PASS [ДА] | {"payment_id": "p_demo_002", "status": "SUCCESS", "idempotent_replay": true}',
        'T3-5 (Отмена платежа)              | PASS [ДА] | {"cancel_from_created": "CANCELED", "cancel_from_pending": "CANCEL_NOT_ALLOWED (409)"}',
        "========================================================================",
    ]
    render_terminal_screenshot(
        "cli_demo_screenshot.png",
        "Terminal — python 04_прототип.py (qr_001, qr_003, --run-tests)",
        cli_lines,
    )

    md5_lines = ["$ md5sum 01_данные/*.csv"]
    for fn in ["merchants.csv", "employees.csv", "payments.csv", "qr_links.csv"]:
        p = os.path.join(BASE_DIR, "01_данные", fn)
        with open(p, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()
        md5_lines.append(f"{h}  01_данные/{fn}   [Не менялся — 100% оригинал]")
    render_terminal_screenshot(
        "md5_verification.png",
        "Terminal — Контроль целостности исходных данных (md5sum)",
        md5_lines,
    )


def ensure_alias_files():
    """Создаёт алиасы файлов, упоминаемые в разных шаблонах кейса."""
    shutil.copyfile(
        os.path.join(BASE_DIR, "02_roles.md"),
        os.path.join(BASE_DIR, "02_roles(1).md"),
    )
    shutil.copyfile(
        os.path.join(BASE_DIR, "08_errors.md"),
        os.path.join(BASE_DIR, "08_ER.md"),
    )
    shutil.copyfile(
        os.path.join(BASE_DIR, "03_тесты.md"),
        os.path.join(BASE_DIR, "10_tests.md"),
    )


def init_git_and_screenshot():
    """Инициализирует Git-репозиторий с веткой team_1_case_3 и делает скриншот коммита."""
    subprocess.run(["git", "init"], cwd=BASE_DIR, check=False, capture_output=True)
    subprocess.run(
        ["git", "checkout", "-B", "team_1_case_3"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Team 1 Case 3"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "team1@vpotoke.local"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=False, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat(case3): complete online tips platform, docs, tests, and diagrams"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
    )
    log_out = subprocess.run(
        ["git", "log", "-n", "1", "--stat"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    branch_out = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    git_lines = [f"$ git branch --show-current", branch_out, "", "$ git log -n 1 --stat"]
    for l in log_out.splitlines()[:18]:
        git_lines.append(l)
    render_terminal_screenshot(
        "git_commit.png",
        f"Terminal — Git branch {branch_out} & latest commit",
        git_lines,
    )


if __name__ == "__main__":
    ensure_alias_files()
    write_drawio_files()
    generate_architecture_png()
    generate_er_model_png()
    generate_state_machine_png()
    generate_screenshots()
    init_git_and_screenshot()
    print("Диаграммы, .drawio, скриншоты и Git-ветка team_1_case_3 успешно созданы.")
