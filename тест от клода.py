#!/usr/bin/env python3
"""
VLESS Config Tester
Тестирует все конфиги из .txt файла, измеряет TCP latency и сортирует по пингу.
Использование: python3 vless_tester.py your_configs.txt
"""

import sys
import socket
import time
import re
import concurrent.futures
from urllib.parse import urlparse, parse_qs, unquote
from dataclasses import dataclass, field

# ─────────────────────────────────────────────
#  Укажите путь к вашему файлу с конфигами
# ─────────────────────────────────────────────
INPUT_FILE = "/Users/q1mai/PycharmProjects/PythonProject1/1111.txt"

# ─────────────────────────────────────────────
#  Настройки
# ─────────────────────────────────────────────
TIMEOUT     = 3.0   # секунд на одно TCP соединение
ATTEMPTS    = 3     # количество попыток для среднего пинга
MAX_WORKERS = 50    # параллельных потоков
TOP_N       = 20    # сколько лучших показывать в итоге

# Цвета ANSI
R  = "\033[0m"
B  = "\033[1m"
G  = "\033[32m"
Y  = "\033[33m"
C  = "\033[36m"
RD = "\033[31m"
GY = "\033[90m"
BL = "\033[34m"
MG = "\033[35m"

# ─────────────────────────────────────────────
#  Структура конфига
# ─────────────────────────────────────────────
@dataclass
class VlessConfig:
    raw: str
    uuid: str = ""
    host: str = ""
    port: int = 443
    security: str = ""
    transport: str = ""
    sni: str = ""
    label: str = ""
    ping_ms: float = -1.0
    error: str = ""

    def type_str(self) -> str:
        parts = []
        if self.security in ("reality", "tls"):
            parts.append(self.security.upper())
        if self.transport:
            parts.append(self.transport.upper())
        return "+".join(parts) if parts else "TCP"

    def supports_udp(self) -> bool:
        """REALITY+TCP и plain TCP лучше всего для UDP-over-proxy (Discord/Roblox)"""
        return self.transport in ("tcp", "") and self.security in ("reality", "none", "")


# ─────────────────────────────────────────────
#  Парсер VLESS URI
# ─────────────────────────────────────────────
def parse_vless(line: str) -> VlessConfig | None:
    line = line.strip()
    if not line.startswith("vless://"):
        return None

    cfg = VlessConfig(raw=line)

    try:
        # Извлекаем fragment (label)
        if "#" in line:
            uri_part, frag = line.rsplit("#", 1)
            cfg.label = unquote(frag)
        else:
            uri_part = line
            cfg.label = ""

        parsed = urlparse(uri_part)
        cfg.uuid = parsed.username or ""
        cfg.host = parsed.hostname or ""
        cfg.port = parsed.port or 443

        params = parse_qs(parsed.query)
        cfg.security  = params.get("security",  ["none"])[0].lower()
        cfg.transport = params.get("type",       ["tcp"])[0].lower()
        cfg.sni       = params.get("sni",        [""])[0]

    except Exception as e:
        cfg.error = str(e)

    return cfg


# ─────────────────────────────────────────────
#  TCP ping
# ─────────────────────────────────────────────
def tcp_ping(host: str, port: int, timeout: float = TIMEOUT) -> float:
    """Возвращает время TCP-рукопожатия в мс, или -1 при ошибке."""
    try:
        # Базовая валидация хоста
        if not host or len(host) > 253:
            return -1.0
        if any(len(label) > 63 for label in host.split(".")):
            return -1.0

        # Резолвим IP заранее — чтобы не учитывать DNS в пинге
        try:
            ip = socket.gethostbyname(host)
        except (socket.gaierror, UnicodeError):
            return -1.0

        start = time.perf_counter()
        with socket.create_connection((ip, port), timeout=timeout):
            pass
        elapsed = (time.perf_counter() - start) * 1000
        return round(elapsed, 2)
    except (socket.timeout, ConnectionRefusedError, OSError):
        return -1.0


def measure_config(cfg: VlessConfig) -> VlessConfig:
    if not cfg.host:
        cfg.error = "no host"
        return cfg

    pings = []
    for _ in range(ATTEMPTS):
        p = tcp_ping(cfg.host, cfg.port)
        if p > 0:
            pings.append(p)

    if pings:
        cfg.ping_ms = round(sum(pings) / len(pings), 1)
    else:
        cfg.ping_ms = -1.0
        cfg.error = "unreachable"

    return cfg


# ─────────────────────────────────────────────
#  Загрузка файла
# ─────────────────────────────────────────────
def load_configs(filepath: str) -> list[VlessConfig]:
    configs = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cfg = parse_vless(line)
                if cfg and cfg.host:
                    configs.append(cfg)
    except FileNotFoundError:
        print(f"{RD}Файл не найден: {filepath}{R}")
        sys.exit(1)
    return configs


# ─────────────────────────────────────────────
#  Прогресс-бар
# ─────────────────────────────────────────────
def progress_bar(done: int, total: int, width: int = 40) -> str:
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{C}{bar}{R}] {done}/{total}"


# ─────────────────────────────────────────────
#  Вывод таблицы результатов
# ─────────────────────────────────────────────
def ping_color(ms: float) -> str:
    if ms < 0:   return f"{RD}DEAD{R}"
    if ms < 80:  return f"{G}{B}{ms:>7.1f} ms{R}"
    if ms < 150: return f"{G}{ms:>7.1f} ms{R}"
    if ms < 300: return f"{Y}{ms:>7.1f} ms{R}"
    return f"{RD}{ms:>7.1f} ms{R}"


def udp_badge(cfg: VlessConfig) -> str:
    return f"{G}UDP✓{R}" if cfg.supports_udp() else f"{GY}    {R}"


def short_label(label: str, max_len: int = 45) -> str:
    # Убираем github.com/... хвосты
    label = re.sub(r'\s*github\.com\S*', '', label).strip()
    if len(label) > max_len:
        label = label[:max_len - 1] + "…"
    return label


def print_results(results: list[VlessConfig]):
    alive  = [c for c in results if c.ping_ms > 0]
    dead   = [c for c in results if c.ping_ms <= 0]
    top    = sorted(alive, key=lambda c: c.ping_ms)[:TOP_N]

    print()
    print(f"{B}{'─'*85}{R}")
    print(f"{B}  ТОП-{TOP_N} конфигов по пингу{R}  {GY}(всего: {len(results)}, живых: {len(alive)}, мёртвых: {len(dead)}){R}")
    print(f"{B}{'─'*85}{R}")
    print(f"  {B}{'#':>3}  {'Пинг':>9}  {'UDP':>4}  {'Тип':<16}  {'Хост':<30}  Название{R}")
    print(f"  {'─'*3}  {'─'*9}  {'─'*4}  {'─'*16}  {'─'*30}  {'─'*25}")

    for i, cfg in enumerate(top, 1):
        host_str = f"{cfg.host}:{cfg.port}"
        if len(host_str) > 30:
            host_str = host_str[:29] + "…"
        label_str = short_label(cfg.label)
        type_str  = cfg.type_str()

        print(f"  {B}{i:>3}{R}  {ping_color(cfg.ping_ms)}  {udp_badge(cfg)}  "
              f"{C}{type_str:<16}{R}  {BL}{host_str:<30}{R}  {GY}{label_str}{R}")

    # ─── UDP-пригодные отдельным блоком ───
    udp_ok = [c for c in top if c.supports_udp()]
    if udp_ok:
        print()
        print(f"{B}{'─'*85}{R}")
        print(f"{B}  🎮 Лучшие для Discord / Roblox (UDP-совместимые){R}")
        print(f"{B}{'─'*85}{R}")
        for i, cfg in enumerate(udp_ok[:10], 1):
            host_str  = f"{cfg.host}:{cfg.port}"
            label_str = short_label(cfg.label)
            print(f"  {B}{i:>2}{R}  {ping_color(cfg.ping_ms)}  {C}{cfg.type_str():<16}{R}  "
                  f"{BL}{host_str:<32}{R}  {GY}{label_str}{R}")
        print()
        print(f"  {G}{B}Совет:{R} Для Discord выбирай конфиги с пингом <100ms и типом REALITY+TCP или TCP.")
        print(f"         Для Roblox то же самое — он использует UDP под капотом, и REALITY+TCP")
        print(f"         туннелирует это лучше всего.")

    print()
    print(f"{B}{'─'*85}{R}")
    print(f"{GY}  💡 Как использовать найденный конфиг в v2rayTun:{R}")
    print(f"     1. Скопируй строку vless://... из файла (по номеру из таблицы выше)")
    print(f"     2. В v2rayTun → Add Server → Paste URL")
    print(f"     3. Включи режим 'TUN' или 'System Proxy' для полного покрытия UDP")
    print(f"{B}{'─'*85}{R}")
    print()


# ─────────────────────────────────────────────
#  Экспорт топа в файл
# ─────────────────────────────────────────────
def export_top(results: list[VlessConfig], out_path: str):
    alive = sorted([c for c in results if c.ping_ms > 0], key=lambda c: c.ping_ms)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Отсортировано по пингу (TCP latency)\n")
        f.write(f"# Всего живых: {len(alive)}\n\n")
        for cfg in alive:
            f.write(f"# ping={cfg.ping_ms}ms type={cfg.type_str()} udp={cfg.supports_udp()}\n")
            f.write(cfg.raw + "\n\n")
    print(f"  {G}✓ Отсортированный список сохранён: {out_path}{R}")


# ─────────────────────────────────────────────
#  Главная функция
# ─────────────────────────────────────────────
def main():
    filepath = INPUT_FILE

    global TOP_N
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            TOP_N = int(sys.argv[idx + 1])

    print(f"\n{B}VLESS Config Tester{R}  {GY}для Discord & Roblox из Турции{R}")
    print(f"{'─'*50}")
    print(f"  Файл:      {C}{filepath}{R}")
    print(f"  Попыток:   {ATTEMPTS} на конфиг")
    print(f"  Таймаут:   {TIMEOUT}с")
    print(f"  Потоков:   {MAX_WORKERS}")
    print()

    configs = load_configs(filepath)
    if not configs:
        print(f"{RD}Не найдено ни одного корректного VLESS конфига в файле.{R}")
        sys.exit(1)

    print(f"  Найдено конфигов: {B}{len(configs)}{R}")
    print(f"  Запускаю тесты...\n")

    results = []
    done = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(measure_config, cfg): cfg for cfg in configs}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            # Обновляем прогресс в той же строке
            print(f"\r  {progress_bar(done, len(configs))}", end="", flush=True)

    print()  # новая строка после прогресс-бара

    print_results(results)

    # Сохраняем отсортированный список рядом с исходным файлом
    base = filepath.rsplit(".", 1)[0]
    out_path = base + "_sorted.txt"
    export_top(results, out_path)


if __name__ == "__main__":
    main()