from .utils import translate

def translation(request):
    lang = getattr(request, 'lang_code', 'en')  # We'll set this from middleware later
    return {
        "t": lambda s: translate(s, lang)
    }