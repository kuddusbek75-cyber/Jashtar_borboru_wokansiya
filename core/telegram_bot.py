import requests
import threading

TELEGRAM_TOKEN = '8824733275:AAGlC7-RWebduCimioMFJeG62Fu5wEvRiN4'
ADMIN_CHAT_ID = '8130952764'
ADMIN_PASSWORD = 'jashtar2026'
TELEGRAM_API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

authorized_users = set()


def send_message(chat_id, text, keyboard=None):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if keyboard:
        data['reply_markup'] = keyboard
    try:
        requests.post(f'{TELEGRAM_API}/sendMessage', json=data, timeout=10)
    except Exception:
        pass


def send_telegram(job):
    salary = job.get_salary_display()
    author = job.author.username if job.author else 'Не указан'
    email = job.author.email if job.author else 'Не указан'

    text = (
        f"🆕 *Новая вакансия на проверку!*\n\n"
        f"📌 *Должность:* {job.title}\n"
        f"🏢 *Компания:* {job.company}\n"
        f"📍 *Город:* {job.location}\n"
        f"💰 *Зарплата:* {salary}\n"
        f"👤 *Автор:* {author}\n"
        f"📧 *Email автора:* {email}\n"
        f"📞 *Контакт:* {job.contact_phone or 'не указан'}\n\n"
        f"🔗 ID вакансии: `{job.pk}`"
    )

    keyboard = {
        'inline_keyboard': [[
            {'text': '✅ Одобрить', 'callback_data': f'approve_{job.pk}'},
            {'text': '❌ Отклонить', 'callback_data': f'reject_{job.pk}'}
        ]]
    }

    send_message(ADMIN_CHAT_ID, text, keyboard)


def send_application_notify(application):
    from django.core.mail import send_mail
    from django.conf import settings

    job = application.job
    applicant = application.applicant

    try:
        profile = applicant.profile
        phone = profile.phone or 'не указан'
        city = profile.city or 'не указан'
    except Exception:
        phone = 'не указан'
        city = 'не указан'

    cover = application.cover_letter or 'не указано'

    # Отправляем email работодателю
    if job.author and job.author.email:
        send_mail(
            subject=f'Новый отклик на вашу вакансию "{job.title}" — Жаштар Борбору',
            message=(
                f'Здравствуйте!\n\n'
                f'На вашу вакансию "{job.title}" поступил новый отклик.\n\n'
                f'━━━━━━━━━━━━━━━━━━━━\n'
                f'Соискатель: {applicant.get_full_name() or applicant.username}\n'
                f'Email: {applicant.email}\n'
                f'Телефон: {phone}\n'
                f'Город: {city}\n'
                f'━━━━━━━━━━━━━━━━━━━━\n\n'
                f'Сопроводительное письмо:\n{cover}\n\n'
                f'━━━━━━━━━━━━━━━━━━━━\n'
                f'Жаштар Борбору — портал вакансий Кыргызстана\n'
                f'http://jashtar-borboru.kg'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[job.author.email],
            fail_silently=True
        )


def process_action(action, job_id, callback_id, chat_id):
    from .models import Job
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        answer_callback(callback_id, 'Вакансия не найдена')
        return

    if action == 'approve':
        job.status = 'approved'
        job.is_active = True
        job.save()
        answer_callback(callback_id, '✅ Одобрено!')
        send_message(chat_id, f'✅ Вакансия *"{job.title}"* одобрена и опубликована на сайте!')
        if job.author and job.author.email:
            send_mail(
                subject='Ваша вакансия одобрена — Жаштар Борбору',
                message=(
                    f'Здравствуйте, {job.author.get_full_name() or job.author.username}!\n\n'
                    f'Ваша вакансия "{job.title}" в компании "{job.company}" '
                    f'одобрена и опубликована на портале.\n\n'
                    f'Жаштар Борбору — портал вакансий Кыргызстана'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[job.author.email],
                fail_silently=True
            )

    elif action == 'reject':
        job.status = 'rejected'
        job.is_active = False
        job.save()
        answer_callback(callback_id, '❌ Отклонено!')
        send_message(chat_id, f'❌ Вакансия *"{job.title}"* отклонена.')
        if job.author and job.author.email:
            send_mail(
                subject='Ваша вакансия отклонена — Жаштар Борбору',
                message=(
                    f'Здравствуйте, {job.author.get_full_name() or job.author.username}!\n\n'
                    f'К сожалению, ваша вакансия "{job.title}" не прошла модерацию.\n'
                    f'Попробуйте подать снова с исправленным описанием.\n\n'
                    f'Жаштар Борбору — портал вакансий Кыргызстана'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[job.author.email],
                fail_silently=True
            )


def answer_callback(callback_id, text):
    try:
        requests.post(f'{TELEGRAM_API}/answerCallbackQuery', json={
            'callback_query_id': callback_id,
            'text': text,
            'show_alert': True
        }, timeout=10)
    except Exception:
        pass


def handle_updates():
    offset = None
    while True:
        try:
            params = {'timeout': 30}
            if offset:
                params['offset'] = offset
            resp = requests.get(
                f'{TELEGRAM_API}/getUpdates',
                params=params,
                timeout=35
            )
            data = resp.json()

            for update in data.get('result', []):
                offset = update['update_id'] + 1

                message = update.get('message')
                if message:
                    chat_id = str(message['chat']['id'])
                    text = message.get('text', '')

                    if text == '/start':
                        if chat_id == ADMIN_CHAT_ID:
                            authorized_users.add(chat_id)
                            send_message(chat_id, '👋 Добро пожаловать! Вы уже авторизованы как администратор.')
                        else:
                            send_message(chat_id, '🔒 Введите пароль для доступа:')

                    elif chat_id != ADMIN_CHAT_ID:
                        if text == ADMIN_PASSWORD:
                            authorized_users.add(chat_id)
                            send_message(chat_id, '✅ Пароль верный! Теперь вы можете управлять вакансиями.')
                        elif chat_id not in authorized_users:
                            send_message(chat_id, '⛔ Неверный пароль. Доступ запрещён.')

                callback = update.get('callback_query')
                if callback:
                    chat_id = str(callback['from']['id'])

                    if chat_id != ADMIN_CHAT_ID and chat_id not in authorized_users:
                        answer_callback(callback['id'], '⛔ Нет доступа. Введите пароль.')
                        continue

                    data_str = callback['data']
                    action, job_id = data_str.split('_', 1)
                    process_action(action, int(job_id), callback['id'], chat_id)

        except Exception:
            import time
            time.sleep(5)


def start_bot():
    t = threading.Thread(target=handle_updates, daemon=True)
    t.start()