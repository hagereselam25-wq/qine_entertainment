from django.utils.deprecation import MiddlewareMixin

class JSONTranslationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # You can use GET param, session, cookie, or default language
        lang = request.GET.get('lang') or request.session.get('lang') or 'en'
        request.lang_code = lang

class LanguageMiddleware:
    def init(self, get_response):
        self.get_response = get_response

    def call(self, request):
        # Detect language from GET param, session, or default
        lang = request.GET.get('lang') or request.session.get('lang', 'en')
        request.lang_code = lang
        request.session['lang'] = lang
        response = self.get_response(request)
        return response