"""
Cybersecurity Password Toolkit - Advanced Edition (Fixed Entropy)
Developer: Mr. Nobi
Year: 2026
Fixed: Accurate charset sizes for true entropy calculation
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import string
import secrets
import math
import re
import hashlib
import time
import threading
import json
import os
from pathlib import Path
from itertools import product
from typing import Set, List

# ---------------- Bundled Data (Portability Fix) ----------------
COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "abc123", "admin",
    "letmein", "welcome", "monkey", "password123", "dragon", "master",
    "football", "baseball", "iloveyou"
}

TOP_PASSWORDS = list(COMMON_PASSWORDS) * 10

ROCKYOU_SET: Set[str] = set()
MANIFEST_FILE = Path(__file__).parent / "password_tool.manifest.json"
STRICT_INTEGRITY_MODE = os.getenv("PASSWORD_TOOL_STRICT_INTEGRITY", "0") == "1"
INTEGRITY_WARNINGS: List[str] = []

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def verify_integrity() -> tuple[bool, List[str]]:
    issues: List[str] = []

    if not MANIFEST_FILE.exists():
        issues.append(f"Manifest missing: {MANIFEST_FILE.name}")
        return False, issues

    try:
        manifest = json.loads(MANIFEST_FILE.read_text())
    except Exception as e:
        issues.append(f"Manifest unreadable: {e}")
        return False, issues

    files = manifest.get("files", {})
    if not isinstance(files, dict) or not files:
        issues.append("Manifest has no file hashes")
        return False, issues

    for rel_path, expected_hash in files.items():
        abs_path = Path(__file__).parent / rel_path
        if not abs_path.exists():
            issues.append(f"Missing file: {rel_path}")
            continue
        actual_hash = _sha256_file(abs_path)
        if actual_hash != expected_hash:
            issues.append(f"Hash mismatch: {rel_path}")

    return len(issues) == 0, issues

def load_wordlist() -> None:
    global ROCKYOU_SET
    script_dir = Path(__file__).parent
    wordlist_path = script_dir / "top_passwords.json"
    
    if wordlist_path.exists():
        try:
            with open(wordlist_path, 'r') as f:
                ROCKYOU_SET = set(json.load(f))
            return
        except Exception:
            pass
    ROCKYOU_SET = set(TOP_PASSWORDS)

load_wordlist()

# ---------------- FIXED Entropy & Crack Time ----------------
def calculate_entropy(password: str) -> float:
    """Accurate: Sum ACTUAL charset sizes used (NIST-style)."""
    if not password:
        return 0.0
    charset_sizes = {
        'ascii_lowercase': 26,
        'ascii_uppercase': 26,
        'digits': 10,
        'punctuation': 32
    }
    used_size = sum(charset_sizes[cat] for cat in charset_sizes 
                    if any(c in getattr(string, cat) for c in password))
    return round(len(password) * math.log2(used_size), 2) if used_size else 0.0

def estimate_crack_time(entropy: float) -> str:
    if entropy == 0:
        return "Invalid"
    guesses = 2 ** entropy
    seconds = guesses / 1e12  # GPU rate
    if seconds < 60: return "Instant"
    elif seconds < 3600: return f"{seconds/60:.0f} Min"
    elif seconds < 86400: return f"{seconds/3600:.0f} Hrs"
    elif seconds < 3.1536e7: return f"{seconds/86400:.0f} Days"
    elif seconds < 3.1536e9: return f"{seconds/3.1536e7:.0f} Years"
    else: return ">1000 Years"

# ---------------- Hybrid Strength Engine ----------------
LEET_MAP = str.maketrans({
    "@": "a", "4": "a",
    "0": "o",
    "$": "s", "5": "s",
    "1": "i", "!": "i",
    "3": "e",
    "7": "t"
})

KEYBOARD_ROWS = [
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "1234567890"
]

def normalize_password(password: str) -> str:
    lowered = password.lower().translate(LEET_MAP)
    return ''.join(ch for ch in lowered if ch.isalnum())

def has_keyboard_sequence(password: str, seq_len: int = 4) -> bool:
    p = password.lower()
    for row in KEYBOARD_ROWS:
        for i in range(len(row) - seq_len + 1):
            seq = row[i:i + seq_len]
            if seq in p or seq[::-1] in p:
                return True
    return False

def has_repeated_pattern(password: str) -> bool:
    if len(password) < 4:
        return False
    if len(set(password)) <= max(1, len(password) // 3):
        return True
    for size in range(1, min(4, len(password) // 2 + 1)):
        if len(password) % size == 0:
            chunk = password[:size]
            if chunk * (len(password) // size) == password:
                return True
    return False

def evaluate_password_strength(password: str) -> dict:
    entropy = calculate_entropy(password)
    crack_time = estimate_crack_time(entropy)
    feedback: List[str] = []

    if not password:
        return {
            "score": 0,
            "strength": "N/A",
            "entropy": 0.0,
            "crack_time": "Invalid",
            "feedback": ["Enter a password"]
        }

    normalized = normalize_password(password)
    lower = password.lower()
    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(c in string.punctuation for c in password)
    ])

    score = 0
    length = len(password)
    if length >= 20: score += 50
    elif length >= 16: score += 40
    elif length >= 12: score += 30
    elif length >= 8: score += 15

    score += classes * 10
    score += int((len(set(password)) / len(password)) * 10)
    if entropy >= 60: score += 10
    elif entropy >= 40: score += 5

    in_common = lower in COMMON_PASSWORDS or password in ROCKYOU_SET
    normalized_common = normalized in ROCKYOU_SET or normalized in COMMON_PASSWORDS
    contains_common = any(word in normalized for word in COMMON_PASSWORDS if len(word) >= 6)
    keyboard_seq = has_keyboard_sequence(password)
    repeated = has_repeated_pattern(password)
    has_year = bool(re.search(r"(19\d{2}|20\d{2})", password))

    if length < 12:
        score -= 15
        feedback.append("⚠️ Use at least 12 characters")
    if classes < 3:
        feedback.append("⚠️ Use 3+ character types (upper/lower/number/symbol)")
    if in_common:
        score -= 60
        feedback.append("❌ Common password")
    if normalized_common and not in_common:
        score -= 50
        feedback.append("❌ Predictable substitution of a common password")
    if contains_common and not normalized_common and not in_common:
        score -= 20
        feedback.append("⚠️ Contains common password term")
    if keyboard_seq:
        score -= 20
        feedback.append("⚠️ Keyboard sequence detected")
    if repeated:
        score -= 20
        feedback.append("⚠️ Repeated pattern detected")
    if has_year:
        score -= 15
        feedback.append("⚠️ Contains a year/date pattern")

    score = max(0, min(100, score))

    if score < 40:
        strength = "WEAK"
    elif score < 80:
        strength = "MODERATE"
    else:
        strength = "STRONG"

    if not feedback:
        feedback.append("✅ Good password structure")

    return {
        "score": score,
        "strength": strength,
        "entropy": entropy,
        "crack_time": crack_time,
        "feedback": feedback
    }

# ---------------- Logger ----------------
log_lock = threading.Lock()
terminal = None

def log(msg: str) -> None:
    if terminal:
        # Tkinter widgets must be updated on the main thread.
        def _append() -> None:
            with log_lock:
                terminal.insert(tk.END, msg + "\n")
                terminal.see(tk.END)
                terminal.update_idletasks()
        terminal.after(0, _append)

# ---------------- Generator ----------------
def generate_password(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(chars) for _ in range(length))

# ---------------- Attacks (unchanged, optimized) ----------------
def dictionary_attack(password: str, max_attempts: int = 10000, progress_cb=None, stop_event=None) -> None:
    log("[ATTACK] Dictionary attack (demo)...")
    if not password:
        log("[INFO] Enter a password first")
        if progress_cb:
            progress_cb(0, "Enter a password first")
        return

    target = password.lower()
    normalized_target = normalize_password(password)
    attempts = 0
    words = sorted(ROCKYOU_SET)[:max_attempts]
    total = max(1, len(words))
    for word in words:
        if stop_event and stop_event.is_set():
            log("[INFO] Dictionary attack stopped by user")
            if progress_cb:
                progress_cb(0, "Dictionary stopped")
            return
        attempts += 1
        if word.lower() == target:
            log(f"[SUCCESS] Cracked: {attempts} attempts")
            if progress_cb:
                progress_cb(100, f"Dictionary success in {attempts} attempts")
            return
        # Detect simple l33t substitutions (e.g., P@ssw0rd -> password)
        if normalize_password(word) == normalized_target:
            log(f"[SUCCESS] Cracked via normalized match: {attempts} attempts")
            if progress_cb:
                progress_cb(100, f"Dictionary normalized success in {attempts} attempts")
            return
        if attempts % 250 == 0:
            log(f"[PROG] {attempts}")
            if progress_cb:
                progress_cb((attempts / total) * 100, f"Dictionary {attempts}/{total}")
    log("[FAILED] Not found (demo)")
    if progress_cb:
        progress_cb(100, f"Dictionary failed after {attempts} attempts")

def brute_force_attack(password: str, max_attempts: int = 5000, progress_cb=None, stop_event=None) -> None:
    log("[ATTACK] Brute force demo...")
    if not password:
        log("[INFO] Enter a password first")
        if progress_cb:
            progress_cb(0, "Enter a password first")
        return

    charset = ""
    if any(c.islower() for c in password):
        charset += string.ascii_lowercase
    if any(c.isupper() for c in password):
        charset += string.ascii_uppercase
    if any(c.isdigit() for c in password):
        charset += string.digits

    if not charset:
        charset = string.ascii_lowercase

    max_demo_len = 8
    if len(password) > max_demo_len:
        log(f"[INFO] Demo brute force capped at {max_demo_len} chars, current length={len(password)}")
        if progress_cb:
            progress_cb(0, f"Brute force demo supports max {max_demo_len} characters (current {len(password)})")
        return

    attempts = 0
    for length in range(1, min(max_demo_len, len(password)) + 1):
        for combo in product(charset, repeat=length):
            if stop_event and stop_event.is_set():
                log("[INFO] Brute force attack stopped by user")
                if progress_cb:
                    progress_cb(0, "Brute force stopped")
                return
            guess = ''.join(combo)
            attempts += 1
            if guess == password:
                log(f"[SUCCESS] Brute: {attempts}")
                if progress_cb:
                    progress_cb(100, f"Brute force success in {attempts} attempts")
                return
            if attempts >= max_attempts:
                log("[INFO] Limit hit")
                if progress_cb:
                    progress_cb(100, f"Brute force limit hit at {attempts} attempts")
                return
            if attempts % 500 == 0 and progress_cb:
                progress_cb((attempts / max_attempts) * 100, f"Brute force {attempts}/{max_attempts}")
    log("[FAILED] Demo")
    if progress_cb:
        progress_cb(100, f"Brute force failed after {attempts} attempts")

def hybrid_attack(password: str, max_attempts: int = 5000, progress_cb=None, stop_event=None) -> None:
    log("[ATTACK] Hybrid demo...")
    if not password:
        log("[INFO] Enter a password first")
        if progress_cb:
            progress_cb(0, "Enter a password first")
        return

    target = password.lower()
    normalized_target = normalize_password(password)
    attempts = 0
    separators = ("", "_", "!", "@")
    bases = sorted(ROCKYOU_SET)[:120]
    prioritized = [b for b in bases if b.lower() in target]
    ordered_bases = prioritized + [b for b in bases if b not in prioritized]

    for base in ordered_bases:
        candidates = [base, base.capitalize()]
        for variant in candidates:
            for sep in separators:
                for num in range(1000):
                    if stop_event and stop_event.is_set():
                        log("[INFO] Hybrid attack stopped by user")
                        if progress_cb:
                            progress_cb(0, "Hybrid stopped")
                        return
                    guess = f"{variant}{sep}{num}"
                    attempts += 1
                    if guess.lower() == target:
                        log(f"[SUCCESS] Hybrid: {attempts}")
                        if progress_cb:
                            progress_cb(100, f"Hybrid success in {attempts} attempts")
                        return
                    if normalize_password(guess) == normalized_target:
                        log(f"[SUCCESS] Hybrid normalized: {attempts}")
                        if progress_cb:
                            progress_cb(100, f"Hybrid normalized success in {attempts} attempts")
                        return
                    if attempts >= max_attempts:
                        log("[INFO] Limit")
                        if progress_cb:
                            progress_cb(100, f"Hybrid limit hit at {attempts} attempts")
                        return
                    if attempts % 500 == 0 and progress_cb:
                        progress_cb((attempts / max_attempts) * 100, f"Hybrid {attempts}/{max_attempts}")
    log("[FAILED] Demo")
    if progress_cb:
        progress_cb(100, f"Hybrid failed after {attempts} attempts")

# ---------------- GUI (with fixed analyze) ----------------
class PasswordApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cybersecurity Password Toolkit v2.1")
        self.geometry("1100x800")
        self.configure(bg="#0b0f19")
        self.resizable(True, True)
        self.show_password = False
        self.attack_running = False
        self.attack_stop_event = threading.Event()
        self.placeholder_text = "Enter password"
        self.placeholder_active = False
        global terminal, progress, strength_label, entropy_label, crack_label, feedback_box
        self.build_ui()
        if INTEGRITY_WARNINGS:
            self._update_attack_ui(0, "Integrity warning")
            for warn in INTEGRITY_WARNINGS:
                log(f"[SECURITY] {warn}")
    
    def build_ui(self):
        global terminal, progress, strength_label, entropy_label, crack_label, feedback_box
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=25, troughcolor="#111827", background="#00ff9f")
        
        # Sidebar
        sidebar = tk.Frame(self, bg="#111827", width=220); sidebar.pack(side="left", fill="y", padx=(0,10)); sidebar.propagate(False)
        tk.Label(sidebar, text="🔒 TOOLS", fg="#00ff9f", bg="#111827", font=("Consolas", 16, "bold")).pack(pady=20)
        tk.Button(sidebar, text="🔍 Analyze", command=self.analyze_password, width=20, bg="#00ff9f", fg="black", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="🎲 Generate", command=self.generate_password, width=20, bg="#00ff9f", fg="black", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="📖 Dictionary", command=self.run_dictionary, width=20, bg="#ff4444", fg="white", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="🔨 Brute Force", command=self.run_bruteforce, width=20, bg="#ff4444", fg="white", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="🔄 Hybrid", command=self.run_hybrid, width=20, bg="#ff4444", fg="white", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="⏹ Stop Attack", command=self.stop_attack, width=20, bg="#aa0000", fg="white", font=("Consolas", 10, "bold")).pack(pady=8)
        tk.Button(sidebar, text="ℹ️ About", command=self.show_about, width=20, bg="#444", fg="white").pack(pady=20)
        
        # Main panel
        main = tk.Frame(self, bg="#0b0f19"); main.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(main, text="CYBERSECURITY PASSWORD TOOLKIT", font=("Consolas", 20, "bold"), fg="#00ff9f", bg="#0b0f19").pack(pady=20)
        
        self.password_entry = tk.Entry(main, font=("Consolas", 14), width=40, show="*", bg="#111827", fg="#00ff9f", insertbackground="#00ff9f")
        self.password_entry.pack(pady=10)
        self.password_entry.bind('<KeyRelease>', self.on_key_release)
        self.password_entry.bind('<FocusIn>', self._on_password_focus_in)
        self.password_entry.bind('<FocusOut>', self._on_password_focus_out)
        self._set_password_placeholder()
        
        self.toggle_btn = tk.Button(main, text="👁️ SHOW", command=self.toggle_password, bg="#444", fg="white", font=("Consolas", 11))
        self.toggle_btn.pack(pady=5)
        
        progress = ttk.Progressbar(main, length=500)
        progress.pack(pady=20)
        
        strength_label = tk.Label(main, text="Strength: N/A", fg="#00ff9f", bg="#0b0f19", font=("Consolas", 16, "bold"))
        strength_label.pack(pady=5)
        entropy_label = tk.Label(main, text="Entropy: 0 bits", fg="white", bg="#0b0f19", font=("Consolas", 12)); entropy_label.pack()
        crack_label = tk.Label(main, text="Crack Time: Invalid", fg="white", bg="#0b0f19", font=("Consolas", 12)); crack_label.pack()
        
        tk.Label(main, text="📋 FEEDBACK", fg="#00ff9f", bg="#0b0f19", font=("Consolas", 14, "bold")).pack(pady=(20,5))
        feedback_box = scrolledtext.ScrolledText(main, height=6, width=70, bg="#111827", fg="#00ff9f", font=("Consolas", 11)); feedback_box.pack(pady=10)
        
        tk.Label(main, text="📜 LOG", fg="#00ff9f", bg="#0b0f19", font=("Consolas", 14, "bold")).pack(pady=(20,5))
        self.attack_status = tk.Label(main, text="Attack Status: Idle", fg="white", bg="#0b0f19", font=("Consolas", 11))
        self.attack_status.pack()
        self.attack_progress = ttk.Progressbar(main, length=500)
        self.attack_progress.pack(pady=8)
        terminal = scrolledtext.ScrolledText(main, height=10, width=90, bg="black", fg="#00ff9f", font=("Consolas", 10)); terminal.pack(fill="x")
        
        tk.Label(self, text="© 2026 Mr. Nobi | Fixed Accurate Entropy", fg="gray", bg="#0b0f19").pack(side="bottom", pady=10)
    
    def on_key_release(self, event=None):
        if self.placeholder_active:
            return
        if hasattr(self, '_analysis_id'): self.after_cancel(self._analysis_id)
        self._analysis_id = self.after(300, self.analyze_password)

    def _set_password_placeholder(self) -> None:
        if self.password_entry.get():
            return
        self.placeholder_active = True
        self.password_entry.config(show="", fg="gray")
        self.password_entry.insert(0, self.placeholder_text)

    def _clear_password_placeholder(self) -> None:
        if not self.placeholder_active:
            return
        self.password_entry.delete(0, tk.END)
        self.placeholder_active = False
        self.password_entry.config(fg="#00ff9f", show="" if self.show_password else "*")

    def _on_password_focus_in(self, event=None):
        self._clear_password_placeholder()

    def _on_password_focus_out(self, event=None):
        if not self.password_entry.get():
            self._set_password_placeholder()
    
    def toggle_password(self):
        self.show_password = not self.show_password
        self.password_entry.config(show="" if self.show_password else "*")
        self.toggle_btn.config(text="👁️ HIDE" if self.show_password else "👁️ SHOW")
    
    def analyze_password(self):
        password = "" if self.placeholder_active else self.password_entry.get()
        feedback_box.delete(1.0, tk.END)
        
        if not password:
            strength_label.config(text="Strength: Enter password", fg="gray")
            entropy_label.config(text="Entropy: 0 bits"); crack_label.config(text="Crack Time: Invalid"); progress['value'] = 0
            return
        
        result = evaluate_password_strength(password)
        entropy = result["entropy"]
        crack_time = result["crack_time"]
        
        entropy_label.config(text=f"Entropy: {entropy} bits")
        crack_label.config(text=f"Crack Time: {crack_time}")

        strength = result["strength"]
        score = result["score"]
        if strength == "WEAK":
            color = "red"
        elif strength == "MODERATE":
            color = "orange"
        else:
            color = "#00ff9f"

        strength_label.config(text=f"Strength: {strength} ({score}/100)", fg=color)
        progress['value'] = score

        for f in result["feedback"]:
            feedback_box.insert(tk.END, f + "\n")
        log(f"[SCAN] score={score} entropy={entropy} bits")
    
    def generate_password(self):
        self._clear_password_placeholder()
        pw = generate_password(); self.password_entry.delete(0, tk.END); self.password_entry.insert(0, pw)
        self.analyze_password(); log("[GEN] Secure password generated")
    
    def _update_attack_ui(self, value: float, status: str) -> None:
        self.attack_progress['value'] = max(0, min(100, value))
        self.attack_status.config(text=f"Attack Status: {status}")

    def _run_attack_thread(self, attack_name: str, attack_fn, max_attempts: int) -> None:
        if self.attack_running:
            log("[INFO] Another attack is already running")
            return
        self.attack_running = True
        self.attack_stop_event.clear()
        self._update_attack_ui(0, f"{attack_name} started...")
        password = "" if self.placeholder_active else self.password_entry.get()

        def progress_cb(value: float, status: str) -> None:
            self.after(0, lambda: self._update_attack_ui(value, status))

        def worker() -> None:
            try:
                attack_fn(password, max_attempts, progress_cb, self.attack_stop_event)
            finally:
                def _finish() -> None:
                    self.attack_running = False
                    if self.attack_stop_event.is_set():
                        self._update_attack_ui(0, "Idle")
                self.after(0, _finish)

        threading.Thread(target=worker, daemon=True).start()

    def run_dictionary(self): self._run_attack_thread("Dictionary", dictionary_attack, 20000)
    def run_bruteforce(self): self._run_attack_thread("Brute Force", brute_force_attack, 50000)
    def run_hybrid(self): self._run_attack_thread("Hybrid", hybrid_attack, 50000)

    def stop_attack(self):
        if not self.attack_running:
            log("[INFO] No attack is running")
            self._update_attack_ui(0, "Idle")
            return
        self.attack_stop_event.set()
        self._update_attack_ui(0, "Stopping...")
        log("[INFO] Stop requested")
    
    def show_about(self):
        messagebox.showinfo("About", "Toolkit v2.1\n\n• FIXED: Accurate entropy (full charset sizes)\n• Real-time + debounced analysis\n• Safe demo attacks\n• Cross-platform\n\nMr. Nobi 2026")

def splash_screen():
    splash = tk.Tk(); splash.geometry("500x300"); splash.configure(bg="#0b0f19"); splash.overrideredirect(True)
    tk.Label(splash, text="PASSWORD TOOLKIT v2.1", font=("Consolas", 16, "bold"), fg="#00ff9f", bg="#0b0f19").pack(pady=40)
    tk.Label(splash, text="Accurate Entropy Fixed...", font=("Consolas", 11), fg="white", bg="#0b0f19").pack()
    tk.Label(splash, text="Mr. Nobi 2026", fg="gray", bg="#0b0f19").pack(side="bottom", pady=20)
    splash.update(); splash.geometry(f"+{(splash.winfo_screenwidth()//2-250)}+{(splash.winfo_screenheight()//2-150)}"); time.sleep(2); splash.destroy()

if __name__ == "__main__":
    integrity_ok, integrity_issues = verify_integrity()
    if not integrity_ok:
        if STRICT_INTEGRITY_MODE:
            details = "\n".join(f"- {i}" for i in integrity_issues[:8])
            messagebox.showerror(
                "Integrity Check Failed",
                "Application files were modified or missing.\n\n"
                "Strict mode is enabled, so startup is blocked.\n\n"
                f"{details}"
            )
            raise SystemExit(1)
        INTEGRITY_WARNINGS = [f"Integrity warning: {i}" for i in integrity_issues]

    splash_screen()
    app = PasswordApp()
    app.mainloop()
