import json
import os
from django.conf import settings

# Cache loaded translations to avoid reloading every request
_translation_cache = {}

def load_translation(lang_code):
    if lang_code in _translation_cache:
        return _translation_cache[lang_code]

    translations_path = os.path.join(settings.BASE_DIR, 'translations', f'{lang_code}.json')
    if not os.path.exists(translations_path):
        # Fallback to English if JSON doesn't exist
        translations_path = os.path.join(settings.BASE_DIR, 'translations', 'en.json')

    with open(translations_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        _translation_cache[lang_code] = data
        return data

def translate(text, lang_code):
    translations = load_translation(lang_code)
    return translations.get(text, text)  # Fallback to original if no translation