import base64
import hashlib
import math
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock

LOGIN_MAX_FAILURES = 5
LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
LOGIN_LOCKOUT_SECONDS = 15 * 60
LOGIN_IP_MAX_FAILURES = 20
LOGIN_IP_WINDOW_SECONDS = 15 * 60

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
COMMON_PASSWORDS = frozenset({
    "password1234", "password12345", "password123456", "123456789012", "1234567890123",
    "qwertyuiop12", "qwerty123456", "iloveyou1234", "letmein12345", "welcome12345",
    "administrator", "changeme1234", "caresight123", "caresight1234", "nurse1234567",
    "hospital1234", "abcdefghijkl", "abc123456789", "passwordpassword", "111111111111",
})


class LoginBlocked(Exception):
    def __init__(self, retry_after):
        super().__init__("Too many sign-in attempts")
        self.retry_after = max(1, math.ceil(retry_after))


class LoginThrottle:

    def __init__(self):
        self._lock = Lock()
        self._failures = defaultdict(deque)
        self._locked_until = {}
        self._ip_failures = defaultdict(deque)

    def reset(self):
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()
            self._ip_failures.clear()

    @staticmethod
    def _trim(entries, window, now):
        while entries and entries[0] <= now - window:
            entries.popleft()

    def check(self, username, ip):
        now = time.time()
        with self._lock:
            failures = self._ip_failures[ip]
            self._trim(failures, LOGIN_IP_WINDOW_SECONDS, now)
            if len(failures) >= LOGIN_IP_MAX_FAILURES:
                raise LoginBlocked(failures[0] + LOGIN_IP_WINDOW_SECONDS - now)

            locked_until = self._locked_until.get(username)
            if locked_until is not None:
                if locked_until > now:
                    raise LoginBlocked(locked_until - now)
                del self._locked_until[username]

    def record_failure(self, username, ip):
        now = time.time()
        with self._lock:
            self._ip_failures[ip].append(now)
            failures = self._failures[username]
            self._trim(failures, LOGIN_FAILURE_WINDOW_SECONDS, now)
            failures.append(now)
            if len(failures) >= LOGIN_MAX_FAILURES:
                self._locked_until[username] = now + LOGIN_LOCKOUT_SECONDS
                failures.clear()
                return True
        return False

    def record_success(self, username):
        with self._lock:
            self._failures.pop(username, None)
            self._locked_until.pop(username, None)


login_throttle = LoginThrottle()


def password_problems(password, username=""):
    if not isinstance(password, str):
        return ["Password is required."]
    problems = []
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        problems.append(f"Password must contain {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters.")
    lowered = password.lower()
    if username and username.lower() in lowered:
        problems.append("Password must not contain the username.")
    if lowered in COMMON_PASSWORDS or (password and re.fullmatch(r"(.)\1*", password)):
        problems.append("Password is too common or easy to guess.")
    return problems


def _inline_script_hashes(html):
    hashes = []
    for script in re.findall(r"<script>(.*?)</script>", html, re.S):
        normalised = script.replace("\r\n", "\n").replace("\r", "\n")
        digest = hashlib.sha256(normalised.encode("utf-8")).digest()
        hashes.append("'sha256-" + base64.b64encode(digest).decode() + "'")
    return hashes


def page_csp(index_path: Path):
    html = index_path.read_text(encoding="utf-8")
    scripts = " ".join(_inline_script_hashes(html)) or "'none'"
    return (
        "default-src 'self'; "
        f"script-src {scripts}; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )


COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
