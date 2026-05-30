from .translations import TRANSLATIONS, t


def lang_context(request):
    lang = request.session.get('lang', 'ru')
    trans = TRANSLATIONS.get(lang, {})
    return {
        'LANG': lang,
        'T': trans,
        'is_ky': lang == 'ky',
    }
