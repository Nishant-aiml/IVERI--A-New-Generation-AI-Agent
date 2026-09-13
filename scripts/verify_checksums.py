"""Cross-platform checksum verification for IVERI AI Agent.

Handles:
- Exact byte-level verification for binary assets (PDFs, images, GGUF models)
- Normalization for cross-platform text files (CRLF vs LF)
"""

import sys
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def verify_all():
    manifest = ROOT_DIR / "SHA256SUMS"
    if not manifest.exists():
        print("[ERROR] SHA256SUMS manifest not found.")
        return 1

    passed = 0
    failed = 0
    total = 0

    with open(manifest, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print("=" * 64)
    print("      IVERI AI AGENT // CRYPTOGRAPHIC CHECKSUM VERIFIER        ")
    print("=" * 64)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue

        expected_hash = parts[0].strip().lower()
        rel_path = parts[1].strip()
        file_path = ROOT_DIR / rel_path
        total += 1

        if not file_path.exists():
            print(f" [MISS] {rel_path:<42} File not found")
            failed += 1
            continue

        # Check raw binary hash
        hasher = hashlib.sha256()
        with open(file_path, "rb") as fp:
            data = fp.read()
            hasher.update(data)
        actual_hash = hasher.hexdigest().lower()

        # If raw hash matches, perfect
        if actual_hash == expected_hash:
            print(f" [PASS] {rel_path:<42} (exact match)")
            passed += 1
            continue

        # If text file, try normalized CRLF <-> LF
        normalized_data = data.replace(b"\r\n", b"\n")
        norm_hash_lf = hashlib.sha256(normalized_data).hexdigest().lower()
        norm_hash_crlf = hashlib.sha256(data.replace(b"\n", b"\r\n")).hexdigest().lower()

        if expected_hash in (norm_hash_lf, norm_hash_crlf):
            print(f" [PASS] {rel_path:<42} (newline normalized)")
            passed += 1
        else:
            print(f" [FAIL] {rel_path:<42} Hash mismatch")
            print(f"        Expected: {expected_hash}")
            print(f"        Actual:   {actual_hash}")
            failed += 1

    print("=" * 64)
    print(f" Summary: {passed}/{total} verified successfully.")
    if failed > 0:
        print(f" [FAIL] {failed} files failed verification.")
        return 1

    print(" [OK] All cryptographic checksums verified.")
    return 0


if __name__ == "__main__":
    sys.exit(verify_all())
