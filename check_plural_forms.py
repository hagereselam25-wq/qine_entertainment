import os
import re

# Path to your locale directory
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")

# Regex to match a valid plural form line
plural_regex = re.compile(r'^"Plural-Forms:\s*nplurals=\d+;\s*plural=.*;\s*\\n"$')

invalid_files = []

for root, dirs, files in os.walk(LOCALE_DIR):
    for file in files:
        if file.endswith(".po"):
            po_path = os.path.join(root, file)
            with open(po_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('"Plural-Forms:'):
                        if not plural_regex.match(line.strip()):
                            invalid_files.append(po_path)
                        break  # Only check first Plural-Forms line

if invalid_files:
    print("⚠️ Invalid Plural-Forms detected in:")
    for f in invalid_files:
        print("  -", f)
else:
    print("✅ All .po files have valid Plural-Forms.")
