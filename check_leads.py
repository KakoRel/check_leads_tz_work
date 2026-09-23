import threading
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TIMEOUT_SEC = 5
LOG_FILE = Path(__file__).with_name("leads_health.log")

SERVICES = [
    ("Formit", "https://formit.fake"),
    ("DataValidator", "https://datavalidator.fake"),
    ("LeadSync", "https://leadsync.fake"),
    ("MailPipe", "https://mailpipe.fake"),
    ("BitDashboard", "https://bitdashboard.fake"),
]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log(line):
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def send_alert(name, url, status, code):
    # имитация отправки
    print(f"Send alert to Telegram: {name} {url} — {status}, код {code}", flush=True)


def request_service(url, bucket):
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=TIMEOUT_SEC) as response:
            bucket["code"] = response.getcode()
    except Exception as exc:
        bucket["error"] = exc


def check_one(name, url):
    bucket = {}
    # отдельный поток, чтобы DNS по .fake не повесил весь скрипт
    worker = threading.Thread(target=request_service, args=(url, bucket), daemon=True)
    worker.start()
    worker.join(TIMEOUT_SEC)

    try:
        if worker.is_alive():
            raise TimeoutError(f"таймаут {TIMEOUT_SEC}с")
        if "error" in bucket:
            raise bucket["error"]
        code = bucket["code"]
        ok = code == 200
        status = "200 OK" if ok else f"неожиданный ответ {code}"
    except HTTPError as exc:
        code = exc.code
        ok = False
        status = f"HTTP ошибка {code}"
    except TimeoutError as exc:
        code = "-"
        ok = False
        status = f"нет ответа ({exc})"
    except URLError as exc:
        code = "-"
        ok = False
        reason = getattr(exc, "reason", exc)
        status = f"нет ответа ({reason})"
    except Exception as exc:
        code = "-"
        ok = False
        status = f"сбой проверки ({exc})"

    line = f"{now()} | {name} | {url} | {status} | код {code}"
    write_log(line)
    print(line, flush=True)

    if not ok:
        send_alert(name, url, status, code)

    return ok


def main():
    print(f"Проверка цепочки лидов, {now()}", flush=True)
    print(f"Лог: {LOG_FILE}\n", flush=True)

    failed = 0
    for name, url in SERVICES:
        if not check_one(name, url):
            failed += 1

    print(flush=True)
    if failed:
        print(f"Готово: проблемных сервисов — {failed} из {len(SERVICES)}", flush=True)
    else:
        print("Готово: все сервисы ответили 200 OK", flush=True)


if __name__ == "__main__":
    main()
