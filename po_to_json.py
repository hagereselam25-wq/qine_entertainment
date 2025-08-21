import polib
import json
import os

# Folder with your .po files
LOCALE_DIR = 'locale'
OUTPUT_DIR = 'translations'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# List your languages (match your .po folders)
languages = ['en', 'am', 'ti']

for lang in languages:
    po_path = os.path.join(LOCALE_DIR, lang, 'LC_MESSAGES', 'django.po')
    if not os.path.exists(po_path):
        print(f"No .po file for {lang}")
        continue

    po = polib.pofile(po_path)
    translations = {}
    for entry in po:
        if entry.msgid.strip():  # skip empty msgid
            translations[entry.msgid] = entry.msgstr

    # Save as JSON
    json_path = os.path.join(OUTPUT_DIR, f"{lang}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"Saved {lang}.json with {len(translations)} strings")