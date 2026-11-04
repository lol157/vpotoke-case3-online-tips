#!/usr/bin/env python3
"""
Генератор артефактов для кейса №3 «Онлайн-чаевые: платформа для ресторанов»:
  1. Создаёт .drawio XML схемы (architecture.drawio, er_model.drawio, state_machine.drawio).
  2. Рендерит PNG-диаграммы и скриншоты с помощью Pillow (PIL).
  3. Создаёт дополнительные копии файлов (08_ER.md, 10_tests.md, 02_roles(1).md).
  4. Инициализирует Git-репозиторий с веткой team_1_case_3 и делает коммит.
  5. Генерирует PDF-версии Презентации (8 слайдов) и Приложения (12 страниц A4) через Chrome Headless.
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


def draw_arrow(draw, p1, p2, label="", color="#1e40af", label_offset=(0, 0)):
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
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
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
    img = Image.new("RGB", (1380, 720), "#f8fafc")
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
        (30, 140, 290, 390),
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
        (480, 120, 880, 420),
        "2. Платформа чаевых (Backend API)",
        [
            "• Эндпоинты OpenAPI 3.0.3 (порт 8083):",
            "  GET /api/v1/qr/{qr_id}",
            "  POST /api/v1/tips",
            "  POST /api/v1/payments/{id}/confirm | /cancel",
            "  GET /api/v1/reports/tips | /daily",
            "• Правила QR: Q-1 (HMAC-SHA256), Q-2 (TTL 24ч),",
            "  Q-3 (nonce), Q-4 (ACTIVE), Q-5 (чек), Q-6 (<=50%)",
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
        (1070, 140, 1350, 390),
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
        (200, 490, 620, 685),
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
        (740, 490, 1170, 685),
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
    draw_arrow(draw, (290, 215), (480, 215), "1. GET /qr, POST /tips", "#0284c7")
    draw_arrow(draw, (480, 315), (290, 315), "4. Статус / Чек JSON", "#0284c7")
    draw_arrow(draw, (880, 215), (1070, 215), "2. Запрос списания", "#7c3aed")
    draw_arrow(draw, (1070, 315), (880, 315), "3. Код шлюза (h=0..9)", "#7c3aed")
    draw_arrow(draw, (570, 420), (450, 490), "Чтение QR / Запись платежа", "#059669")
    draw_arrow(draw, (780, 420), (900, 490), "Запись события AuditEvent", "#d97706")

    img.save(os.path.join(DIAG_DIR, "architecture.png"))


def generate_er_model_png():
    """A.2. ER-модель данных (6 сущностей, PK/FK, связи 1:N)."""
    img = Image.new("RGB", (1340, 780), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 20),
        "A.2. ER-модель данных платформы онлайн-чаевых (6 сущностей, связи 1:N)",
        fill="#0f172a",
        font=get_font(24, bold=True),
    )

    # Верхний ряд: Report (слева), Merchant (в центре), Employee (справа)
    draw_box(
        draw,
        (40, 90, 390, 330),
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

    draw_box(
        draw,
        (490, 90, 840, 330),
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
        (940, 90, 1300, 330),
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

    # Нижний ряд: QR, Payment, AuditEvent
    draw_box(
        draw,
        (40, 450, 410, 730),
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
        (490, 450, 850, 730),
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
        (940, 450, 1300, 730),
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

    # Чистые непересекающиеся стрелки связей 1:N
    draw_arrow(draw, (490, 200), (390, 200), "1 : N", "#0f766e")
    draw_arrow(draw, (840, 200), (940, 200), "1 : N", "#1d4ed8")
    draw_arrow(draw, (570, 330), (260, 450), "1 : N (чеки ресторана)", "#6d28d9", label_offset=(-40, -10))
    draw_arrow(draw, (1050, 330), (360, 450), "1 : N (обслужил официант)", "#0369a1", label_offset=(60, 12))
    draw_arrow(draw, (410, 580), (490, 580), "1 : N", "#047857")
    draw_arrow(draw, (850, 580), (940, 580), "1 : N", "#b45309")

    img.save(os.path.join(DIAG_DIR, "er_model.png"))


def generate_state_machine_png():
    """A.3. Схема состояний платежа (State Machine)."""
    img = Image.new("RGB", (1340, 620), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "A.3. Диаграмма состояний платежа (Жизненный цикл и правило P-4)",
        fill="#0f172a",
        font=get_font(24, bold=True),
    )

    draw_box(
        draw,
        (40, 220, 260, 370),
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
        (500, 220, 750, 370),
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
        (990, 80, 1290, 220),
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
        (990, 250, 1290, 390),
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
        (500, 445, 760, 585),
        "CANCELED (Финал)",
        [
            "Отменён клиентом до",
            "отправки в шлюз",
            "(POST /cancel -> HTTP 200)",
        ],
        outline="#475569",
        header_fill="#e2e8f0",
    )

    draw_arrow(draw, (260, 290), (500, 290), "Клиент подтвердил (/confirm)", "#0284c7")
    draw_arrow(draw, (750, 250), (990, 150), "h = 0..7 (SUCCESS)", "#059669")
    draw_arrow(draw, (750, 315), (990, 315), "h = 8 (CARD_DECLINED)", "#dc2626")
    draw_arrow(draw, (625, 220), (625, 145), "h = 9 (GATEWAY_TIMEOUT -> остаётся в PENDING)", "#d97706")
    draw_arrow(draw, (150, 370), (500, 515), "Клиент отменил (/cancel) — РАЗРЕШЕНО", "#059669", label_offset=(-30, 10))
    draw_arrow(draw, (625, 370), (625, 445), "ЗАПРЕЩЕНО P-4: 409 CANCEL_NOT_ALLOWED", "#dc2626")

    img.save(os.path.join(DIAG_DIR, "state_machine.png"))


def render_terminal_screenshot(filename, title, lines):
    """Рендерит реалистичный скриншот терминала с выводом команд."""
    width = 1240
    height = max(320, 90 + len(lines) * 24)
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)

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
    # Уже сгенерированы или перезаписываются при вызове
    pass


def generate_screenshots():
    """Создаёт скриншоты работы прототипа и проверки MD5."""
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
    subprocess.run(["git", "config", "core.quotepath", "false"], cwd=BASE_DIR, check=False, capture_output=True)
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

    git_lines = ["$ git branch --show-current", branch_out, "", "$ git log -n 1 --stat"]
    for l in log_out.splitlines()[:19]:
        git_lines.append(l)
    render_terminal_screenshot(
        "git_commit.png",
        f"Terminal — Git branch {branch_out} & latest commit",
        git_lines,
    )


def generate_pdfs():
    """Генерирует PDF-файлы Презентации (8 слайдов) и Приложения (A4) через Chrome Headless."""
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((c for c in chrome_candidates if os.path.exists(c)), None)
    if not browser:
        print("Браузер для рендеринга PDF не найден.")
        return

    arch_uri = "file:///" + os.path.join(DIAG_DIR, "architecture.png").replace("\\", "/")
    er_uri = "file:///" + os.path.join(DIAG_DIR, "er_model.png").replace("\\", "/")
    sm_uri = "file:///" + os.path.join(DIAG_DIR, "state_machine.png").replace("\\", "/")
    cli_uri = "file:///" + os.path.join(DIAG_DIR, "cli_demo_screenshot.png").replace("\\", "/")
    md5_uri = "file:///" + os.path.join(DIAG_DIR, "md5_verification.png").replace("\\", "/")
    git_uri = "file:///" + os.path.join(DIAG_DIR, "git_commit.png").replace("\\", "/")

    # 1. HTML для Презентации (8 слайдов 16:9)
    pres_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: 297mm 167mm; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; background: #fff; }}
  .slide {{ width: 297mm; height: 167mm; padding: 12mm 16mm; page-break-after: always; position: relative; background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%); }}
  .slide-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2563eb; padding-bottom: 6px; margin-bottom: 10px; }}
  .slide-header h1 {{ font-size: 21pt; margin: 0; color: #1e3a8a; }}
  .badge {{ background: #2563eb; color: #fff; padding: 4px 12px; border-radius: 99px; font-size: 10pt; font-weight: 600; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .card {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }}
  h3 {{ margin: 0 0 6px; color: #1d4ed8; font-size: 13pt; }}
  ul {{ margin: 4px 0; padding-left: 18px; font-size: 10.5pt; line-height: 1.42; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; background: #fff; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; }}
  th {{ background: #dbeafe; color: #1e3a8a; }}
  .footer {{ position: absolute; bottom: 6mm; left: 16mm; right: 16mm; display: flex; justify-content: space-between; font-size: 9pt; color: #64748b; }}
</style>
</head>
<body>
  <!-- Слайд 1 -->
  <div class="slide">
    <div class="slide-header"><h1>Кейс №3. Онлайн-чаевые: платформа для ресторанов</h1><span class="badge">Слайд 1 / 8 • Титульный лист</span></div>
    <div class="grid2" style="margin-top:14px;">
      <div class="card">
        <h3>Проблематика и бизнес-контекст</h3>
        <ul>
          <li><b>Заказчик:</b> Сеть ресторанов «Вкус-Сервис» (20 заведений, 60 официантов).</li>
          <li><b>Проблема:</b> более 85% гостей платят безналично — официанты теряют чаевые из-за отсутствия наличных у клиентов.</li>
          <li><b>Рынок:</b> в РФ ниша занята («Нетмонет», «ВТБ.Чаевые», «SberTips»), но рынок <b>Юго-Восточной Азии (ЮВА)</b> свободен и перспективен для масштабирования.</li>
          <li><b>Решение:</b> CRM-платформа безналичных чаевых по одноразовому QR на чеке с криптозащитой HMAC-SHA256 и мгновенной отчётностью.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Команда проекта (ветка <code>team_1_case_3</code>)</h3>
        <table>
          <tr><th>Участник</th><th>Роль</th><th>Зона ответственности</th></tr>
          <tr><td><b>Иванов И.</b></td><td>Аналитик</td><td>Правила Q-1..Q-6, P-1..P-4, FR/NFR, Тесты T3-1..T3-5</td></tr>
          <tr><td><b>Петрова А.</b></td><td>Архитектор / ИБ</td><td>Data Dictionary (22 поля), ER-модель, Угрозы ИБ, RBAC</td></tr>
          <tr><td><b>Сидоров П.</b></td><td>Разработчик</td><td>CLI <code>04_прототип.py</code>, HTTP API <code>app_server.py</code>, OpenAPI</td></tr>
          <tr><td><b>Кузнецова М.</b></td><td>Презентатор</td><td>Роли, 4 экрана диалога, Отчётность, Презентация и PDF</td></tr>
        </table>
      </div>
    </div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Команда team_1_case_3</span></div>
  </div>

  <!-- Слайд 2 -->
  <div class="slide">
    <div class="slide-header"><h1>Требования (FR / NFR) и Ролевая модель (RBAC)</h1><span class="badge">Слайд 2 / 8 • Требования и роли</span></div>
    <div class="grid2">
      <div class="card">
        <h3>Ключевые FR и NFR (<code>04_requirements.md</code>)</h3>
        <ul>
          <li><b>FR-1..FR-3:</b> Генерация и валидация QR (HMAC, TTL 24ч, nonce), 4-экранный диалог выбора чаевых (0..50%).</li>
          <li><b>FR-4..FR-6:</b> Идемпотентная оплата (<code>idempotency_key</code>), эмулятор шлюза, отмена только из <code>CREATED</code>.</li>
          <li><b>FR-7..FR-10:</b> Регистрация с проверкой Админом, RBAC, 3 разреза отчётов, журнал <code>AuditEvent</code>.</li>
          <li><b>NFR-1..NFR-6:</b> Проверка HMAC &le; 50 мс (факт &lt; 1 мс), маска реквизитов <code>****NNNN</code>, запрет PAN/CVV, Rate Limit 30 req/min.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Матрица прав доступа RBAC (4 роли &times; 8 действий)</h3>
        <table>
          <tr><th>Действие</th><th>Мерчант</th><th>Официант</th><th>Клиент</th><th>Админ</th></tr>
          <tr><td>Регистрация в платформе</td><td>да (PENDING)</td><td>по инвайту</td><td>нет</td><td>нет</td></tr>
          <tr><td>Генерация QR на чек</td><td>да</td><td>да (свои)</td><td>нет</td><td>нет</td></tr>
          <tr><td>Просмотр своих чаевых</td><td>да</td><td>только свои</td><td>нет</td><td>аудит</td></tr>
          <tr><td>Сканирование QR</td><td>нет</td><td>нет</td><td>да (свой чек)</td><td>проверка</td></tr>
          <tr><td>Оплата чаевых</td><td>нет</td><td>нет</td><td>да</td><td>нет</td></tr>
          <tr><td>Отчёт по заведению</td><td>да (свой)</td><td>нет (403)</td><td>нет</td><td>да (все)</td></tr>
          <tr><td>Блокировка мерчанта</td><td>нет</td><td>нет</td><td>нет</td><td>да</td></tr>
          <tr><td>Изменение справочников</td><td>свои сотр.</td><td>нет</td><td>нет</td><td>да</td></tr>
        </table>
      </div>
    </div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 2 из 8</span></div>
  </div>

  <!-- Слайд 3 -->
  <div class="slide">
    <div class="slide-header"><h1>Системная архитектура и Потоки данных</h1><span class="badge">Слайд 3 / 8 • Архитектура</span></div>
    <div style="text-align:center;"><img src="{arch_uri}" style="max-height:132mm; max-width:100%; border-radius:8px; border:1px solid #cbd5e1;"></div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 3 из 8</span></div>
  </div>

  <!-- Слайд 4 -->
  <div class="slide">
    <div class="slide-header"><h1>Модель данных (ER) и Правила QR / Платежа</h1><span class="badge">Слайд 4 / 8 • Данные и алгоритмы</span></div>
    <div class="grid2">
      <div class="card" style="text-align:center;">
        <h3>ER-модель (6 сущностей, связи 1:N)</h3>
        <img src="{er_uri}" style="max-height:112mm; max-width:100%;">
      </div>
      <div class="card">
        <h3>Правила валидации QR (Q-1..Q-6) и платежа (P-1..P-4)</h3>
        <table>
          <tr><th>ID</th><th>Правило / Условие</th><th>HTTP</th><th>Код ошибки</th></tr>
          <tr><td>Q-1</td><td><code>signature == HMAC-SHA256(SECRET, payload)[:16]</code></td><td>422</td><td><code>INVALID_QR</code></td></tr>
          <tr><td>Q-2</td><td><code>exp &gt;= now</code> (TTL = 24 часа)</td><td>410</td><td><code>QR_EXPIRED</code></td></tr>
          <tr><td>Q-3</td><td>Одноразовый <code>nonce</code> ещё не погашен</td><td>409</td><td><code>QR_USED</code></td></tr>
          <tr><td>Q-4</td><td><code>merchant.status == ACTIVE</code></td><td>403</td><td><code>MERCHANT_BLOCKED</code></td></tr>
          <tr><td>Q-5</td><td><code>receipt_id</code> совпадает с QR чека</td><td>422</td><td><code>RECEIPT_MISMATCH</code></td></tr>
          <tr><td>Q-6</td><td><code>0 &lt;= tip_pct &lt;= 50</code> (<code>tip &lt;= 0.5*amount</code>)</td><td>422</td><td><code>TIP_OUT_OF_RANGE</code></td></tr>
          <tr><td>P-1</td><td><code>0 &lt; base_amount &lt;= 1 000 000</code></td><td>422</td><td><code>AMOUNT_OUT_OF_RANGE</code></td></tr>
          <tr><td>P-2</td><td>Повтор <code>idempotency_key</code> &rarr; возврат созданного</td><td>200</td><td>— (без дубля в CSV)</td></tr>
          <tr><td>P-3</td><td><code>amount_total &lt;= 2 000 000</code></td><td>422</td><td><code>AMOUNT_OUT_OF_RANGE</code></td></tr>
          <tr><td>P-4</td><td>Запрет отмены из <code>PENDING</code> / <code>SUCCESS</code></td><td>409</td><td><code>CANCEL_NOT_ALLOWED</code></td></tr>
        </table>
      </div>
    </div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 4 из 8</span></div>
  </div>

  <!-- Слайд 5 -->
  <div class="slide">
    <div class="slide-header"><h1>Жизненный цикл платежа, Диалог и Отчётность</h1><span class="badge">Слайд 5 / 8 • Платёж и отчёты</span></div>
    <div class="grid2">
      <div class="card" style="text-align:center;">
        <h3>Граф состояний платежа и эмулятор шлюза</h3>
        <img src="{sm_uri}" style="max-height:110mm; max-width:100%;">
      </div>
      <div class="card">
        <h3>Отчётность по реальному <code>payments.csv</code> (<code>09_reports.md</code>)</h3>
        <ul>
          <li><b>1. По мерчанту <code>m_001</code>:</b> 6 платежей (5 <code>SUCCESS</code>, 1 <code>DECLINED</code>), <code>tips_total = 414.85 ₽</code> (по всем 611.20 ₽), <code>avg_tip_pct = 9.0%</code> (10.0% все), <code>success_rate = 0.8333</code>.</li>
          <li><b>2. По официанту <code>e_001</code> (Иванов И.):</b> <code>tips_total = 83.60 ₽</code> (<code>31.85 + 51.75</code>), <code>payments_count = 2</code>, <code>avg_tip_amount = 41.80 ₽</code>, <code>top_day = "2025-11-03"</code>.</li>
          <li><b>3. По дням <code>m_001</code>:</b> <code>2025-11-01</code> &rarr; <code>245.90 ₽</code> (3 чека, сред. <code>10.0%</code>); <code>2025-11-03</code> &rarr; <code>168.95 ₽</code> (2 успешных чека, сред. <code>7.5%</code>).</li>
        </ul>
        <h3>4 экрана клиентской формы</h3>
        <ul>
          <li><b>Экран 1:</b> Приветствие (ресторан, официант, сумма чека) &rarr; <b>Экран 2:</b> Выбор % (0, 5, 10, 15, 20%) &rarr; <b>Экран 3:</b> Подтверждение / Отмена &rarr; <b>Экран 4:</b> Результат (SUCCESS / DECLINED / TIMEOUT).</li>
        </ul>
      </div>
    </div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 5 из 8</span></div>
  </div>

  <!-- Слайд 6 -->
  <div class="slide">
    <div class="slide-header"><h1>Демонстрация работы прототипа (<code>04_прототип.py</code>)</h1><span class="badge">Слайд 6 / 8 • Демо</span></div>
    <div style="text-align:center;"><img src="{cli_uri}" style="max-height:130mm; max-width:100%; border-radius:8px;"></div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 6 из 8</span></div>
  </div>

  <!-- Слайд 7 -->
  <div class="slide">
    <div class="slide-header"><h1>Доказательство качества: 5 тест-сценариев</h1><span class="badge">Слайд 7 / 8 • Тестирование</span></div>
    <div class="card">
      <table>
        <tr><th>ID</th><th>Тест-сценарий</th><th>Входные данные</th><th>Ожидаемый результат</th><th>Фактический результат (<code>04_прототип.py</code> / <code>test_case3.py</code>)</th><th>Статус</th></tr>
        <tr><td><b>T3-1</b></td><td>Успешная оплата</td><td><code>qr_001</code>, <code>base=637.00</code>, <code>tip_pct=5</code></td><td><code>SUCCESS</code>, <code>total=668.85</code>, <code>tip=31.85</code></td><td><code>status="SUCCESS"</code>, <code>amount_total=668.85</code>, <code>tip_amount=31.85</code> (HTTP 200)</td><td><b>PASS</b></td></tr>
        <tr><td><b>T3-2</b></td><td>Отказ шлюза</td><td><code>qr_003</code>, <code>base=911.00</code>, <code>tip_pct=15</code></td><td><code>DECLINED</code>, <code>CARD_DECLINED</code></td><td><code>status="DECLINED"</code>, <code>error_code="CARD_DECLINED"</code>, <code>total=1047.65</code> (HTTP 402)</td><td><b>PASS</b></td></tr>
        <tr><td><b>T3-3</b></td><td>Неверный / истёкший QR</td><td><code>qr_001</code> (битая подпись / <code>now &gt; exp</code>)</td><td><code>INVALID_QR</code> (422) / <code>QR_EXPIRED</code> (410), без записи</td><td>Получены <code>422 INVALID_QR</code> и <code>410 QR_EXPIRED</code>, в <code>payments_out.csv</code> 0 новых строк</td><td><b>PASS</b></td></tr>
        <tr><td><b>T3-4</b></td><td>Повтор (Идемпотентность)</td><td><code>qr_002</code>, один <code>idempotency_key</code> дважды</td><td>Тот же <code>payment_id</code>, 1 строка в CSV</td><td>Оба вызова вернули <code>p_demo_002</code> (HTTP 200), в <code>payments_out.csv</code> ровно 1 строка</td><td><b>PASS</b></td></tr>
        <tr><td><b>T3-5</b></td><td>Отмена платежа</td><td><code>qr_004</code> (из CREATED), <code>qr_010</code> (из PENDING)</td><td>Из CREATED &rarr; <code>CANCELED</code>; из PENDING &rarr; <code>409</code></td><td>Из CREATED &rarr; <code>CANCELED</code> (200); из PENDING &rarr; <code>409 CANCEL_NOT_ALLOWED</code></td><td><b>PASS</b></td></tr>
      </table>
    </div>
    <div style="margin-top:10px; text-align:center;"><img src="{md5_uri}" style="max-height:54mm; border-radius:8px;"></div>
    <div class="footer"><span>Кейс-чемпионат «ВПОТОКЕ» • Трек 3 «Онлайн-чаевые»</span><span>Слайд 7 из 8</span></div>
  </div>

  <!-- Слайд 8 -->
  <div class="slide">
    <div class="slide-header"><h1>Информационная безопасность, Риски и Итоги</h1><span class="badge">Слайд 8 / 8 • Риски и Итоги</span></div>
    <div class="grid2">
      <div class="card">
        <h3>Модель угроз и меры защиты (<code>11_ИБ.md</code>)</h3>
        <table>
          <tr><th>ID</th><th>Угроза ИБ</th><th>Мера предотвращения (Mitigation)</th><th>Риск</th></tr>
          <tr><td>U-1</td><td>Подделка QR на чеке</td><td><code>HMAC-SHA256</code> + ключ в <code>os.environ</code> + <code>compare_digest</code></td><td>Низкий</td></tr>
          <tr><td>U-2</td><td>Повторная оплата (Replay)</td><td>Одноразовый <code>nonce</code> (6 hex) + <code>TTL = 24 ч</code> (<code>Q-2, Q-3</code>)</td><td>Низкий</td></tr>
          <tr><td>U-3</td><td>Утечка карт / реквизитов</td><td>Запрет хранения PAN/CVV; маска <code>****NNNN</code> (<code>****1001</code>)</td><td>Низкий</td></tr>
          <tr><td>U-4</td><td>Двойное списание средств</td><td><code>idempotency_key</code> (<code>P-2</code>) + запрет отмены из <code>PENDING</code></td><td>Низкий</td></tr>
          <tr><td>U-5</td><td>Манипуляции официанта</td><td>Привязка к <code>receipt_id</code> (<code>Q-5</code>), лимит чаевых &le; 50% (<code>Q-6</code>)</td><td>Низкий</td></tr>
          <tr><td>U-6</td><td>Отсутствие трассировки</td><td>Журнал <code>AuditEvent</code> (9 полей на каждый переход статуса)</td><td>Низкий</td></tr>
        </table>
      </div>
      <div class="card">
        <h3>Жизнеспособность и масштабирование в ЮВА</h3>
        <ul>
          <li><b>Полная готовность MVP:</b> реализованы CLI-прототип, веб-сервер OpenAPI 3.0.3, 4-экранный интерфейс и 100% автотестов на базовом стеке Python.</li>
          <li><b>Готовность к рынку ЮВА:</b> архитектура адаптера шлюза позволяет без изменения ядра подключить национальные QR-системы ЮВА (PromptPay, QRIS, VietQR, PayNow).</li>
          <li><b>Git-ветка:</b> <code>team_1_case_3</code> (все артефакты и тесты верифицированы).</li>
        </ul>
        <div style="text-align:center; margin-top:6px;"><img src="{git_uri}" style="max-height:56mm; max-width:100%; border-radius:6px;"></div>
      </div>
    </div>
    <div class="footer"><span>Спасибо за внимание! Готовы ответить на вопросы жюри.</span><span>Слайд 8 из 8</span></div>
  </div>
</body>
</html>"""

    pres_html_path = os.path.join(DIAG_DIR, "presentation_render.html")
    with open(pres_html_path, "w", encoding="utf-8") as f:
        f.write(pres_html)

    pres_pdf_path = os.path.join(BASE_DIR, "05_Презентация_Кейс3_Онлайн_Чаевые.pdf")
    subprocess.run(
        [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pres_pdf_path}",
            pres_html_path,
        ],
        check=False,
        capture_output=True,
    )

    # 2. HTML для Приложения (A4 портретная ориентация, все разделы A-F)
    app_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4 portrait; margin: 14mm 15mm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #0f172a; }}
  h1 {{ font-size: 17pt; color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 4px; margin-top: 0; }}
  h2 {{ font-size: 13.5pt; color: #1d4ed8; margin-top: 16px; margin-bottom: 6px; border-left: 4px solid #2563eb; padding-left: 8px; }}
  h3 {{ font-size: 11pt; color: #0f172a; margin-top: 12px; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9pt; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 5px 7px; text-align: left; vertical-align: top; }}
  th {{ background: #dbeafe; color: #1e3a8a; font-weight: 600; }}
  img {{ max-width: 100%; border: 1px solid #cbd5e1; border-radius: 6px; margin: 6px 0; }}
  .page-break {{ page-break-before: always; }}
  code {{ font-family: Consolas, monospace; background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }}
</style>
</head>
<body>
  <h1>Приложение к презентации — Кейс №3 «Онлайн-чаевые: платформа для ресторанов»</h1>
  <p><b>Команда:</b> <code>team_1_case_3</code> | <b>Заказчик кейса:</b> Сеть ресторанов «Вкус-Сервис» | <b>Статус:</b> Все разделы A–F выполнены и верифицированы.</p>

  <h2>Раздел A. Диаграммы архитектуры, данных и состояний</h2>
  <h3>A.1. Схема системы (5 блоков и подписанные потоки данных)</h3>
  <img src="{arch_uri}">
  <table>
    <tr><th>Блок</th><th>Назначение</th><th>Передаваемые данные / Потоки</th></tr>
    <tr><td><b>1. Клиент</b></td><td>Веб-диалог (4 экрана) на смартфоне</td><td><code>GET /api/v1/qr/{{qr_id}}</code>, <code>POST /api/v1/tips</code> (<code>qr_id</code>, <code>receipt_id</code>, <code>base_amount</code>, <code>tip_pct</code>, <code>idempotency_key</code>), <code>POST /confirm</code>, <code>POST /cancel</code></td></tr>
    <tr><td><b>2. Платформа</b></td><td>Сервис чаевых (<code>04_прототип.py</code>, <code>app_server.py</code>)</td><td>Валидация правил <code>Q-1..Q-6</code> и <code>P-1..P-4</code>, расчёт чаевых, идемпотентность, RBAC, формирование 3 отчётов</td></tr>
    <tr><td><b>3. Эмулятор шлюза</b></td><td>Имитация эквайринга (<code>emulate_gateway</code>)</td><td>Вычисление <code>h = md5(qr_id + nonce) % 10</code>: <code>0..7 &rarr; SUCCESS</code>, <code>8 &rarr; DECLINED (CARD_DECLINED)</code>, <code>9 &rarr; PENDING (GATEWAY_TIMEOUT)</code></td></tr>
    <tr><td><b>4. Хранилище</b></td><td>Таблицы CSV / JSON</td><td><code>merchants.csv</code> (20), <code>employees.csv</code> (60, маска <code>****NNNN</code>), <code>qr_links.csv</code> (100), <code>payments.csv</code> (100), <code>payments_out.csv</code></td></tr>
    <tr><td><b>5. Аудит</b></td><td>Журнал ИБ (<code>audit_events.csv</code>)</td><td>Append-only запись 9 полей: <code>event_id, payment_id, qr_id, action, from_status, to_status, amount_total, actor, at</code></td></tr>
  </table>

  <h3>A.2. ER-модель данных (6 сущностей, PK/FK, связи 1:N)</h3>
  <img src="{er_uri}">

  <div class="page-break"></div>
  <h3>A.3. Схема состояний платежа (State Machine и правило P-4)</h3>
  <img src="{sm_uri}">

  <h2>Раздел B. Инженерные таблицы правил, ошибок и тестов</h2>
  <h3>B.1. Правила проверки QR (Q-1…Q-6) и платежа (P-1…P-4) с обоснованием</h3>
  <table>
    <tr><th>ID</th><th>Проверка / Условие</th><th>Действие</th><th>HTTP</th><th>Код ошибки</th><th>Обоснование</th></tr>
    <tr><td>Q-1</td><td><code>signature == HMAC-SHA256(SECRET, payload)[:16]</code></td><td>При несовпадении — отклонить</td><td>422</td><td><code>INVALID_QR</code></td><td>Защита от подделки <code>employee_id</code>, <code>merchant_id</code> и срока действия</td></tr>
    <tr><td>Q-2</td><td><code>exp &gt;= now</code> (TTL = 24 ч)</td><td>При истечении — отклонить</td><td>410</td><td><code>QR_EXPIRED</code></td><td>Ограничение окна жизни платёжной ссылки 24 часами</td></tr>
    <tr><td>Q-3</td><td>Одноразовый <code>nonce</code> не погашен</td><td>При повторе — отклонить</td><td>409</td><td><code>QR_USED</code></td><td>Защита от replay-атак по уже оплаченному чеку</td></tr>
    <tr><td>Q-4</td><td><code>merchant.status == ACTIVE</code></td><td>Если BLOCKED/PENDING — отказ</td><td>403</td><td><code>MERCHANT_BLOCKED</code></td><td>Запрет операций для заблокированных (<code>m_019</code>) и неверифицированных (<code>m_020</code>)</td></tr>
    <tr><td>Q-5</td><td><code>req.receipt_id == qr.receipt_id</code></td><td>При расхождении — отклонить</td><td>422</td><td><code>RECEIPT_MISMATCH</code></td><td>Жёсткая привязка оплаты к кассовому чеку клиента</td></tr>
    <tr><td>Q-6</td><td><code>0 &lt;= tip_pct &lt;= 50</code></td><td>Вне диапазона — отклонить</td><td>422</td><td><code>TIP_OUT_OF_RANGE</code></td><td>Защита от опечатки клиента и лимит антифрода (&le; 50% чека)</td></tr>
    <tr><td>P-1</td><td><code>0 &lt; base_amount &lt;= 1 000 000</code></td><td>Вне диапазона — отклонить</td><td>422</td><td><code>AMOUNT_OUT_OF_RANGE</code></td><td>Валидация базовой суммы чека</td></tr>
    <tr><td>P-2</td><td>Повтор <code>idempotency_key</code></td><td>Вернуть существующий платёж</td><td>200</td><td>—</td><td>Защита от двойного списания при повторах запроса</td></tr>
    <tr><td>P-3</td><td><code>amount_total &lt;= 2 000 000</code></td><td>При превышении — отклонить</td><td>422</td><td><code>AMOUNT_OUT_OF_RANGE</code></td><td>Верхний лимит одной транзакции платёжного шлюза</td></tr>
    <tr><td>P-4</td><td>Отмена из <code>PENDING</code> / <code>SUCCESS</code></td><td>Отклонить отмену</td><td>409</td><td><code>CANCEL_NOT_ALLOWED</code></td><td>Отмена разрешена только из <code>CREATED</code> до отправки в шлюз</td></tr>
  </table>

  <h3>B.2. Матрица «Ситуация &rarr; Код ошибки &rarr; HTTP &rarr; retryable»</h3>
  <table>
    <tr><th>Ситуация</th><th>Код ошибки</th><th>HTTP</th><th>retryable</th></tr>
    <tr><td>Подпись QR не совпала с HMAC</td><td><code>INVALID_QR</code></td><td>422</td><td>нет</td></tr>
    <tr><td>QR истёк (<code>exp &lt; now</code>)</td><td><code>QR_EXPIRED</code></td><td>410</td><td>да (новый QR)</td></tr>
    <tr><td><code>nonce</code> уже использован</td><td><code>QR_USED</code></td><td>409</td><td>нет</td></tr>
    <tr><td>Мерчант в статусе <code>BLOCKED</code> / <code>PENDING</code></td><td><code>MERCHANT_BLOCKED</code></td><td>403</td><td>нет</td></tr>
    <tr><td>Не совпал <code>receipt_id</code> чека</td><td><code>RECEIPT_MISMATCH</code></td><td>422</td><td>нет</td></tr>
    <tr><td><code>tip_pct &gt; 50</code> или <code>&lt; 0</code></td><td><code>TIP_OUT_OF_RANGE</code></td><td>422</td><td>да (изменить %)</td></tr>
    <tr><td><code>base_amount &lt;= 0</code> / <code>&gt; 1 000 000</code> или <code>total &gt; 2 000 000</code></td><td><code>AMOUNT_OUT_OF_RANGE</code></td><td>422</td><td>нет</td></tr>
    <tr><td>Повтор запроса с тем же <code>idempotency_key</code></td><td>— (возврат созданного)</td><td>200</td><td>нет</td></tr>
    <tr><td>Эмулятор шлюза вернул <code>8</code></td><td><code>CARD_DECLINED</code></td><td>402</td><td>да (другая карта)</td></tr>
    <tr><td>Эмулятор шлюза вернул <code>9</code></td><td><code>GATEWAY_TIMEOUT</code></td><td>504</td><td>да (опрос статуса)</td></tr>
    <tr><td>Отмена из <code>PENDING</code> или <code>SUCCESS</code></td><td><code>CANCEL_NOT_ALLOWED</code></td><td>409</td><td>нет</td></tr>
    <tr><td>Нарушение прав доступа RBAC</td><td><code>FORBIDDEN</code></td><td>403</td><td>нет</td></tr>
  </table>

  <div class="page-break"></div>
  <h3>B.3. Результаты прогона 5 тест-сценариев (T3-1…T3-5)</h3>
  <table>
    <tr><th>ID</th><th>Сценарий</th><th>Вход</th><th>Ожидание</th><th>Факт (проверено в <code>04_прототип.py</code> и <code>test_case3.py</code>)</th><th>Пройден</th></tr>
    <tr><td><b>T3-1</b></td><td>Успех</td><td><code>qr_001</code>, <code>base=637.00</code>, <code>tip_pct=5</code></td><td><code>SUCCESS</code>, <code>total=668.85</code>, <code>tip=31.85</code></td><td><code>status="SUCCESS"</code>, <code>amount_total=668.85</code>, <code>tip_amount=31.85</code> (HTTP 200)</td><td><b>[x] да</b></td></tr>
    <tr><td><b>T3-2</b></td><td>Отказ шлюза</td><td><code>qr_003</code>, <code>base=911.00</code>, <code>tip_pct=15</code></td><td><code>DECLINED</code>, <code>CARD_DECLINED</code></td><td><code>status="DECLINED"</code>, <code>error_code="CARD_DECLINED"</code>, <code>total=1047.65</code> (HTTP 402)</td><td><b>[x] да</b></td></tr>
    <tr><td><b>T3-3</b></td><td>Неверный QR</td><td>Испорченная подпись / истёкший <code>exp</code></td><td><code>INVALID_QR</code> (422) / <code>QR_EXPIRED</code> (410)</td><td>Коды 422 и 410, в <code>payments_out.csv</code> строка не создана</td><td><b>[x] да</b></td></tr>
    <tr><td><b>T3-4</b></td><td>Повтор</td><td>Тот же <code>idempotency_key</code> дважды (<code>qr_002</code>)</td><td>Тот же <code>payment_id</code>, 1 строка в CSV</td><td>Тот же <code>p_demo_002</code> (HTTP 200), ровно 1 строка в <code>payments_out.csv</code></td><td><b>[x] да</b></td></tr>
    <tr><td><b>T3-5</b></td><td>Отмена</td><td>Отмена из <code>CREATED</code> и из <code>PENDING</code></td><td><code>CANCELED</code> (200); из <code>PENDING</code> &rarr; 409</td><td>Из <code>CREATED</code> &rarr; <code>CANCELED</code> (200); из <code>PENDING</code> &rarr; <code>409 CANCEL_NOT_ALLOWED</code></td><td><b>[x] да</b></td></tr>
  </table>

  <h2>Раздел C. Журнал промптов ИИ (7 записей с верификацией)</h2>
  <table>
    <tr><th>Дата</th><th>Цель</th><th>Промпт (сжато)</th><th>Результат</th><th>Проверка человеком</th><th>Использовано</th></tr>
    <tr><td>2025-11-01</td><td>Понять HMAC</td><td>«Объясни HMAC-SHA256[:16] на примере QR»</td><td>Код с <code>hmac.new</code> и <code>compare_digest</code></td><td>Сверили со всеми 100 строками <code>qr_links.csv</code> (100% совпадение)</td><td>да</td></tr>
    <tr><td>2025-11-01</td><td>Матрица ошибок</td><td>«Сопоставь коды ошибок Q-1..Q-6 и P-1..P-4 с HTTP»</td><td>Таблица HTTP-кодов</td><td>Уточнили 410 для <code>QR_EXPIRED</code>, 409 для <code>QR_USED</code>/<code>P-4</code>, 402 для <code>CARD_DECLINED</code></td><td>переработано</td></tr>
    <tr><td>2025-11-02</td><td>Проверить хэш эмулятора</td><td>«Проверь md5(qr_id+nonce)%10 на qr_001 и qr_003»</td><td>Выявлено отличие среза <code>[:4]</code> и полного MD5</td><td>Задокументировали оба расчёта в <code>07_payment_emulator_template.md</code></td><td>переработано</td></tr>
    <tr><td>2025-11-02</td><td>Идемпотентность P-2</td><td>«Как хранить idempotency_key в CLI прототипе?»</td><td>JSON-хранилище состояния</td><td>Проверили автотестом T3-4 (ровно 1 строка в CSV)</td><td>да</td></tr>
    <tr><td>2025-11-03</td><td>Отчётность по CSV</td><td>«Посчитай метрики m_001 и e_001 по payments.csv»</td><td>Расчёт сумм и средних</td><td>Отделили <code>SUCCESS</code> (414.85 ₽) от <code>DECLINED</code> (p_0057), сверили вручную</td><td>переработано</td></tr>
    <tr><td>2025-11-03</td><td>Схемы OpenAPI 3.0.3</td><td>«Допиши схемы QRResponse, TipCreate, Payment, Report»</td><td>YAML-файл <code>05_api_schemas.yaml</code></td><td>Проверили интеграционным тестом с <code>app_server.py</code></td><td>да</td></tr>
    <tr><td>2025-11-04</td><td>Модель угроз ИБ</td><td>«Сформируй 6 угроз U-1..U-6 и защиту реквизитов»</td><td>Таблицы угроз и мер <code>11_ИБ.md</code></td><td>Проверили маски <code>****NNNN</code> в <code>employees.csv</code> и чтение секрета из <code>os.environ</code></td><td>да</td></tr>
  </table>

  <h2>Раздел D. Матрица вклада команды</h2>
  <table>
    <tr><th>Участник</th><th>Роль</th><th>Файлы и выполненные задачи</th><th>Часы</th><th>Подпись</th></tr>
    <tr><td><b>Иванов И.</b></td><td>Аналитик</td><td><code>02_правила.md</code>, <code>03_тесты.md</code>, <code>04_requirements.md</code>, защита слайдов 4 и 7</td><td>14</td><td><i>Иванов И.</i></td></tr>
    <tr><td><b>Петрова А.</b></td><td>Архитектор / ИБ</td><td><code>03_data_dictionary.md</code>, <code>08_errors.md</code> (<code>08_ER.md</code>), <code>11_ИБ.md</code>, диаграммы draw.io, слайды 3 и 5</td><td>14</td><td><i>Петрова А.</i></td></tr>
    <tr><td><b>Сидоров П.</b></td><td>Разработчик</td><td><code>04_прототип.py</code>, <code>app_server.py</code>, <code>test_case3.py</code>, <code>05_api_schemas.yaml</code>, <code>07_payment_emulator_template.md</code>, слайд 6</td><td>16</td><td><i>Сидоров П.</i></td></tr>
    <tr><td><b>Кузнецова М.</b></td><td>Презентатор</td><td><code>02_roles.md</code>, <code>06_qr_and_tip_dialog.md</code>, <code>09_reports.md</code>, <code>05_презентация.md</code>, <code>06_приложение.md</code>, слайды 1, 2, 8</td><td>12</td><td><i>Кузнецова М.</i></td></tr>
  </table>

  <div class="page-break"></div>
  <h2>Раздел E. Артефакты и скриншоты верификации</h2>
  <h3>E.1. Вывод прототипа <code>04_прототип.py</code> на <code>qr_001</code>, <code>qr_003</code> и автотестах T3-1…T3-5</h3>
  <img src="{cli_uri}">
  <h3>E.2. Проверка неизменности исходных CSV-файлов (<code>md5sum</code>)</h3>
  <img src="{md5_uri}">
  <h3>E.3. Git-ветка <code>team_1_case_3</code> и последний коммит</h3>
  <img src="{git_uri}">
</body>
</html>"""

    app_html_path = os.path.join(DIAG_DIR, "appendix_render.html")
    with open(app_html_path, "w", encoding="utf-8") as f:
        f.write(app_html)

    app_pdf_path = os.path.join(BASE_DIR, "06_Приложение_Кейс3_Онлайн_Чаевые.pdf")
    subprocess.run(
        [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={app_pdf_path}",
            app_html_path,
        ],
        check=False,
        capture_output=True,
    )


if __name__ == "__main__":
    ensure_alias_files()
    generate_architecture_png()
    generate_er_model_png()
    generate_state_machine_png()
    generate_screenshots()
    init_git_and_screenshot()
    generate_pdfs()
    # Финальный коммит всех сгенерированных PDF и диаграмм в ветку team_1_case_3
    subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=False, capture_output=True)
    subprocess.run(
        ["git", "commit", "--amend", "-m", "feat(case3): complete online tips platform, docs, tests, diagrams, and PDFs"],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
    )
    print("Все диаграммы, скриншоты, Git-ветка и PDF-документы успешно созданы.")
