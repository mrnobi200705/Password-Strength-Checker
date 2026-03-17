#!/usr/bin/env python3
"""
Benchmark runner for password_tool.py.

Creates a deterministic labeled dataset and evaluates the model's
WEAK/MODERATE/STRONG classification accuracy.
"""

import argparse
import importlib.util
import json
import random
import string
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).parent
TOOL_FILE = BASE_DIR / "password_tool.py"
DATASET_FILE = BASE_DIR / "password_benchmark_dataset.json"

COMMON = [
    "password", "admin", "qwerty", "letmein", "welcome", "dragon",
    "monkey", "football", "baseball", "abc123", "iloveyou"
]


def load_tool():
    spec = importlib.util.spec_from_file_location("pwtool3", TOOL_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_weak_samples():
    weak = set()

    weak.update({
        "123456", "12345678", "qwerty", "password", "admin", "abc123",
        "letmein", "welcome", "monkey", "dragon", "password123", "111111",
        "aaaaaa", "asdfgh", "qwerty123", "passw0rd", "P@ssw0rd", "Password123"
    })

    for word in COMMON:
        weak.add(word)
        weak.add(word + "123")
        weak.add(word + "2026")
        weak.add(word.capitalize() + "1")

    for seq in ("1234", "12345", "123456", "abcd", "qwer", "asdf", "zxcv"):
        weak.add(seq * 2)
        weak.add(seq + "!!")

    return [{"password": p, "label": "WEAK"} for p in sorted(weak)]


def build_moderate_samples(n=100):
    rng = random.Random(20260307)
    moderate = set()
    words = [
        "Cloud", "Tiger", "Matrix", "Delta", "Cyber", "Orbit", "Falcon",
        "Neon", "Pixel", "Rocket", "Nova", "Apex", "Signal", "Vector"
    ]
    symbols = "!@#$"

    while len(moderate) < n:
        w1 = rng.choice(words)
        w2 = rng.choice(words).lower()
        yy = str(rng.randint(1995, 2029))
        sym = rng.choice(symbols)
        # Intentionally includes year patterns so it stays mostly moderate.
        pw = f"{w1}{sym}{w2}{yy}"
        if 10 <= len(pw) <= 14:
            moderate.add(pw)

    return [{"password": p, "label": "MODERATE"} for p in sorted(moderate)]


def build_strong_samples(n=100):
    rng = random.Random(20260308)
    strong = set()
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    punct = "!@#$%^&*()-_=+[]{}<>?"
    all_chars = lower + upper + digits + punct

    while len(strong) < n:
        length = rng.randint(16, 22)
        pw = [
            rng.choice(lower),
            rng.choice(upper),
            rng.choice(digits),
            rng.choice(punct),
        ]
        pw += [rng.choice(all_chars) for _ in range(length - 4)]
        rng.shuffle(pw)
        candidate = "".join(pw)
        if "password" in candidate.lower() or "qwerty" in candidate.lower():
            continue
        strong.add(candidate)

    return [{"password": p, "label": "STRONG"} for p in sorted(strong)]


def generate_dataset():
    data = []
    data.extend(build_weak_samples())
    data.extend(build_moderate_samples())
    data.extend(build_strong_samples())
    return data


def evaluate(module, dataset):
    total = len(dataset)
    correct = 0
    confusion = Counter()
    by_label = Counter()
    by_label_correct = Counter()
    mismatches = []

    for row in dataset:
        password = row["password"]
        expected = row["label"]
        predicted = module.evaluate_password_strength(password)["strength"]

        by_label[expected] += 1
        confusion[(expected, predicted)] += 1

        if predicted == expected:
            correct += 1
            by_label_correct[expected] += 1
        else:
            mismatches.append((password, expected, predicted))

    accuracy = (correct / total) * 100 if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "by_label": by_label,
        "by_label_correct": by_label_correct,
        "confusion": confusion,
        "mismatches": mismatches,
    }


def print_report(report):
    print(f"Total: {report['total']}")
    print(f"Correct: {report['correct']}")
    print(f"Accuracy: {report['accuracy']:.2f}/100")
    print("")
    print("Per-class accuracy:")
    for label in ("WEAK", "MODERATE", "STRONG"):
        total = report["by_label"][label]
        good = report["by_label_correct"][label]
        pct = (good / total * 100) if total else 0.0
        print(f"  {label:<8} {good}/{total} ({pct:.2f}%)")
    print("")
    print("Confusion matrix (expected -> predicted):")
    for exp in ("WEAK", "MODERATE", "STRONG"):
        row = []
        for pred in ("WEAK", "MODERATE", "STRONG"):
            row.append(f"{report['confusion'][(exp, pred)]:>4}")
        print(f"  {exp:<8} {' '.join(row)}")
    print("")

    if report["mismatches"]:
        print("Sample mismatches:")
        for pw, exp, pred in report["mismatches"][:20]:
            print(f"  {pw!r} expected={exp} predicted={pred}")
    else:
        print("No mismatches.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-dataset",
        action="store_true",
        help=f"Write generated dataset to {DATASET_FILE.name}",
    )
    parser.add_argument(
        "--use-saved-dataset",
        action="store_true",
        help=f"Load {DATASET_FILE.name} if present instead of generating",
    )
    args = parser.parse_args()

    if args.use_saved_dataset and DATASET_FILE.exists():
        dataset = json.loads(DATASET_FILE.read_text())
    else:
        dataset = generate_dataset()

    if args.save_dataset:
        DATASET_FILE.write_text(json.dumps(dataset, indent=2))
        print(f"Saved dataset: {DATASET_FILE}")

    module = load_tool()
    report = evaluate(module, dataset)
    print_report(report)


if __name__ == "__main__":
    main()
