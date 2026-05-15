import os
import sys
import time
import random
import string
import ctypes
import threading
import requests
from dotenv import load_dotenv

load_dotenv()

WHITE = "\033[97m"
GRAY = "\033[37m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BRIGHT_GREEN = "\033[1;92m"
BRIGHT_RED = "\033[1;91m"
RESET = "\033[0m"

def log(msg, tag="::", color=None):
    c = color or WHITE
    print(f"{c}[{tag}] {msg}{RESET}")

def log_ok(msg):     log(msg, "++", WHITE)
def log_info(msg):   log(msg, "::", WHITE)
def log_warn(msg):   log(msg, "!!", YELLOW)
def log_err(msg):    log(msg, "xx", RED)
def log_hit(msg):    print(f"{BRIGHT_GREEN}[>>] {msg}{RESET}")
def log_fail(msg):   print(f"{BRIGHT_RED}[--] {msg}{RESET}")

WEBHOOK_3L     = os.getenv("WEBHOOK_3L", "").strip()
WEBHOOK_4L     = os.getenv("WEBHOOK_4L", "").strip()
TOKENS_FILE    = os.getenv("TOKENS_FILE", "tokens.txt").strip()
PROXIES_FILE   = os.getenv("PROXIES_FILE", "proxies.txt").strip()
HITS_FILE      = os.getenv("HITS_FILE", "hits.txt").strip()
DEFAULT_THREADS = int(os.getenv("DEFAULT_THREADS", "100"))
USE_PROXIES    = os.getenv("USE_PROXIES", "true").lower() in ("1", "true", "yes", "y")

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def load_proxies():
    if not USE_PROXIES or not os.path.exists(PROXIES_FILE):
        return []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

TOKENS = load_tokens()

stats = {"hits": 0, "fails": 0, "rate_limits": 0, "errors": 0, "checks": 0}
stats_lock  = threading.Lock()
tokens_lock = threading.Lock()

token_lockouts = {t: 0 for t in TOKENS}
valid_tokens   = []
proxies_list   = []

def check_token(token):
    try:
        r = requests.get(
            "https://discord.com/api/v9/users/@me",
            headers={"Authorization": token},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False

def random_username(length):
    chars = string.ascii_lowercase + string.digits
    while True:
        u = "".join(random.choices(chars, k=length))
        if u[0] not in "._" and u[-1] not in "._" and ".." not in u and "__" not in u:
            return u

def get_random_headers(token):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ]
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": random.choice(user_agents),
        "Accept": "*/*",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "fr",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIn0=",
    }

def send_webhook(username):
    webhook_url = WEBHOOK_3L if len(username) == 3 else WEBHOOK_4L
    if not webhook_url or "discord.com/api/webhooks" not in webhook_url:
        return
    try:
        requests.post(webhook_url, json={"content": f"`{username}`"}, timeout=5)
    except Exception:
        pass

def title_updater():
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        with stats_lock:
            checks  = stats["checks"]
            hits    = stats["hits"]
            rl      = stats["rate_limits"]
            err     = stats["errors"]
        cpm = (checks / elapsed) * 60 if elapsed > 0 else 0
        with tokens_lock:
            active = len(valid_tokens)
        title = (
            f"[ vgsociety :: ] Hits: {hits} | RL: {rl} | ERR: {err} "
            f"| CPM: {int(cpm)} | Tokens: {active}/{len(TOKENS)}"
        )
        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        time.sleep(1)

def worker():
    session = requests.Session()
    while True:
        with tokens_lock:
            if not valid_tokens:
                break
            now = time.time()
            available = [t for t in valid_tokens if now > token_lockouts.get(t, 0)]
            token = random.choice(available) if available else None

        if not token:
            time.sleep(1)
            continue

        length   = random.choice([3, 4])
        username = random_username(length)
        headers  = get_random_headers(token)

        proxy_dict = None
        if proxies_list:
            p = random.choice(proxies_list)
            if p.startswith("//"):
                p = "http:" + p
            elif "://" not in p:
                p = "http://" + p
            proxy_dict = {"http": p, "https": p}

        try:
            time.sleep(random.uniform(0.1, 0.5))
            req = session.post(
                "https://discord.com/api/v9/users/@me/pomelo-attempt",
                headers=headers,
                json={"username": username},
                proxies=proxy_dict,
                timeout=7,
            )

            with stats_lock:
                stats["checks"] += 1

            if req.status_code == 200:
                data = req.json()
                if data.get("taken") is False:
                    with stats_lock:
                        stats["hits"] += 1
                    log_hit(f"HIT :: {username}")
                    threading.Thread(target=send_webhook, args=(username,), daemon=True).start()
                    with open(HITS_FILE, "a", encoding="utf-8") as f:
                        f.write(username + "\n")
                else:
                    with stats_lock:
                        stats["fails"] += 1
                    log_fail(f"taken :: {username}")

            elif req.status_code == 429:
                with stats_lock:
                    stats["rate_limits"] += 1
                try:
                    data = req.json()
                    delay = data.get("retry_after", 5)
                    if delay > 1000:
                        delay = delay / 1000.0
                except Exception:
                    delay = 30
                with tokens_lock:
                    token_lockouts[token] = time.time() + delay
                log_warn(f"Rate Limit :: attente {int(delay)}s")

            elif req.status_code == 401:
                with tokens_lock:
                    if token in valid_tokens:
                        valid_tokens.remove(token)
                        log_err(f"Token mort :: {token[:15]}...")

            elif req.status_code == 403:
                with stats_lock:
                    stats["errors"] += 1
                with tokens_lock:
                    token_lockouts[token] = time.time() + 10
                log_warn("403 :: Proxy/Token bloque temporairement")

            else:
                with stats_lock:
                    stats["errors"] += 1

        except Exception:
            with stats_lock:
                stats["errors"] += 1

def banner():
    os.system("cls" if os.name == "nt" else "clear")
    art = r"""
  ██▒   █▓   ▄████           ██████  ▒█████   ▄████▄   ██▓ ▓█████ ▄▄▄█████▓ ▓██   ██▓
 ▓██░   █▒  ██▒ ▀█▒        ▒██    ▒ ▒██▒  ██▒▒██▀ ▀█  ▓██▒ ▓█   ▀ ▓  ██▒ ▓▒  ▒██  ██▒
  ▓██  █▒░ ▒██░▄▄▄░        ░ ▓██▄   ▒██░  ██▒▒▓█    ▄ ▒██▒ ▒███   ▒ ▓██░ ▒░   ▒██ ██░
   ▒██ █░░ ░▓█  ██▓          ▒   ██▒▒██   ██░▒▓▓▄ ▄██▒░██░ ▒▓█  ▄ ░ ▓██▓ ░    ░ ▐██▓░
    ▒▀█░   ░▒▓███▀▒        ▒██████▒▒░ ████▓▒░▒ ▓███▀ ░░██░ ░▒████▒  ▒██▒ ░    ░ ██▒▓░
    ░ ▐░    ░▒   ▒         ▒ ▒▓▒ ▒ ░░ ▒░▒░▒░ ░ ░▒ ▒  ░░▓   ░░ ▒░ ░  ▒ ░░       ██▒▒▒ 
    ░ ░░     ░   ░         ░ ░▒  ░ ░  ░ ▒ ▒░   ░  ▒    ▒ ░  ░ ░  ░    ░        ▓██ ░ 
      ░░   ░ ░   ░         ░  ░  ░  ░ ░ ░ ▒  ░          ▒ ░    ░     ░          ▒ ░  
       ░         ░               ░      ░ ░  ░          ░      ░  ░            ░     
      ░                                      ░                                       
"""
    print(f"{WHITE}{art}{RESET}")

def main():
    banner()

    if not TOKENS:
        log_err(f"Aucun token trouve dans '{TOKENS_FILE}'.")
        log_info("Cree ce fichier et mets 1 token par ligne.")
        input("Entree pour quitter...")
        return

    log_info("Validation des tokens...")
    for t in TOKENS:
        if check_token(t):
            with tokens_lock:
                valid_tokens.append(t)
            log_ok(f"OK   :: {t[:25]}...")
        else:
            log_err(f"MORT :: {t[:25]}...")

    if not valid_tokens:
        log_err("Aucun token valide. Arret.")
        input("Entree pour quitter...")
        return

    global proxies_list
    proxies_list = load_proxies()
    if USE_PROXIES:
        log_ok(f"{len(proxies_list)} proxies charges depuis '{PROXIES_FILE}'.")
    else:
        log_info("Proxies desactives via .env (USE_PROXIES=false).")

    try:
        raw = input(f"{WHITE}[::] Threads [{DEFAULT_THREADS}]: {RESET}")
        threads_count = int(raw) if raw.strip() else DEFAULT_THREADS
    except ValueError:
        threads_count = DEFAULT_THREADS

    if proxies_list and len(proxies_list) < (threads_count / 2):
        log_warn(f"Peu de proxies ({len(proxies_list)}) pour {threads_count} threads.")
        log_warn("Risque eleve de Rate Limit.")

    print(f"{GRAY}{'-' * 60}{RESET}")

    threading.Thread(target=title_updater, daemon=True).start()
    for _ in range(threads_count):
        threading.Thread(target=worker, daemon=True).start()

    try:
        while True:
            time.sleep(2)
            with tokens_lock:
                if not valid_tokens:
                    log_err("Plus aucun token valide. Fin.")
                    break
    except KeyboardInterrupt:
        log_warn("Arret demande par l'utilisateur.")

    print(f"{GRAY}{'=' * 30}{RESET}")
    log_info("Session terminee.")
    with stats_lock:
        log_ok(f"Hits   :: {stats['hits']}")
        log_ok(f"Checks :: {stats['checks']}")
        log_ok(f"Errors :: {stats['errors']}")
    print(f"{GRAY}{'=' * 30}{RESET}")
    input("\nEntree pour fermer...")

if __name__ == "__main__":
    main()
