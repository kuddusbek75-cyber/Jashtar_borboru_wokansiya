from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
import logging

logger = logging.getLogger(__name__)

from .models import Job, Category, UserProfile, JobApplication, SupportTicket
from .forms import RegisterForm, ProfileForm, JobPostForm


def home_view(request):
    recent_jobs = Job.objects.filter(is_active=True).order_by('-created_at')[:6]
    featured_jobs = Job.objects.filter(is_active=True, is_featured=True).order_by('-created_at')[:4]
    categories = Category.objects.all()
    total_jobs = Job.objects.filter(is_active=True).count()
    total_companies = Job.objects.filter(is_active=True).values('company').distinct().count()
    total_categories = Category.objects.count()
    return render(request, 'core/home.html', {
        'recent_jobs': recent_jobs,
        'featured_jobs': featured_jobs,
        'categories': categories,
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'total_categories': total_categories,
    })


def transliterate(text):
    lat_to_cyr = {
        'smm': 'смм', 'it': 'ит', 'hr': 'хр',
        'a': 'а', 'b': 'б', 'c': 'с', 'd': 'д', 'e': 'е',
        'f': 'ф', 'g': 'г', 'h': 'х', 'i': 'и', 'j': 'й',
        'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о',
        'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т',
        'u': 'у', 'v': 'в', 'w': 'в', 'x': 'кс', 'y': 'й', 'z': 'з',
    }
    t = text.lower()
    result = set([t])
    converted = ''
    i = 0
    while i < len(t):
        found = False
        for length in [3, 2, 1]:
            chunk = t[i:i+length]
            if chunk in lat_to_cyr:
                converted += lat_to_cyr[chunk]
                i += length
                found = True
                break
        if not found:
            converted += t[i]
            i += 1
    result.add(converted)
    return list(result)


SYNONYMS = {
    'программист': ['разработчик', 'developer', 'python', 'java', 'it', 'ит', '1с', 'программер'],
    'разработчик': ['программист', 'developer', 'it', 'ит', 'девелопер'],
    'it': ['ит', 'айти', 'программист', 'разработчик'],
    'ит': ['it', 'айти', 'программист', 'разработчик'],
    'айти': ['it', 'ит', 'программист'],
    '1с': ['бухгалтерия', 'программист', '1c', 'учёт'],
    'сисадмин': ['системный администратор', 'it', 'ит', 'техподдержка'],
    'техподдержка': ['сисадмин', 'it', 'ит', 'поддержка'],
    'смм': ['smm', 'маркетинг', 'контент', 'инстаграм', 'таргет', 'соцсети', 'тикток'],
    'smm': ['смм', 'маркетинг', 'контент', 'инстаграм', 'таргет', 'тикток'],
    'маркетинг': ['смм', 'smm', 'реклама', 'продвижение', 'контент', 'таргет', 'пиар'],
    'таргетолог': ['таргет', 'смм', 'smm', 'реклама', 'маркетинг'],
    'копирайтер': ['текст', 'контент', 'редактор', 'журналист'],
    'пиар': ['pr', 'маркетинг', 'реклама', 'продвижение'],
    'мобилограф': ['фотограф', 'видеограф', 'съемка', 'оператор', 'фото', 'видео'],
    'фотограф': ['мобилограф', 'видеограф', 'съемка', 'фото', 'оператор'],
    'видеограф': ['мобилограф', 'фотограф', 'монтаж', 'видео', 'оператор'],
    'монтажер': ['монтаж', 'видеограф', 'видео', 'редактор'],
    'оператор': ['видеограф', 'фотограф', 'съемка', 'монтаж'],
    'дизайнер': ['дизайн', 'figma', 'photoshop', 'ui', 'ux', 'графика'],
    'дизайн': ['дизайнер', 'figma', 'photoshop', 'ui', 'ux', 'графика'],
    'аниматор': ['дизайн', 'видео', 'анимация', 'motion'],
    'швея': ['шитье', 'пошив', 'ателье', 'фабрика', 'закройщик', 'текстиль'],
    'закройщик': ['швея', 'шитье', 'пошив', 'ателье', 'кройка'],
    'модельер': ['швея', 'дизайн', 'пошив', 'закройщик', 'мода'],
    'портной': ['швея', 'ателье', 'пошив', 'ремонт одежды'],
    'текстиль': ['швея', 'закройщик', 'фабрика', 'пошив'],
    'продавец': ['кассир', 'торговля', 'магазин', 'консультант', 'сатуучу'],
    'сатуучу': ['продавец', 'кассир', 'торговля', 'магазин'],
    'кассир': ['продавец', 'торговля', 'магазин', 'касса'],
    'консультант': ['продавец', 'менеджер', 'торговля', 'клиент'],
    'мерчандайзер': ['торговля', 'магазин', 'выкладка', 'супермаркет'],
    'риэлтор': ['недвижимость', 'продажи', 'аренда', 'квартира'],
    'официант': ['официантка', 'ресторан', 'кафе', 'бармен', 'гостиница'],
    'бармен': ['официант', 'ресторан', 'кафе', 'бар'],
    'повар': ['кулинар', 'шеф', 'кухня', 'ресторан', 'аш пазы', 'пекарь'],
    'шеф': ['повар', 'кулинар', 'кухня', 'шеф-повар'],
    'аш пазы': ['повар', 'кулинар', 'кухня', 'шеф'],
    'пекарь': ['повар', 'хлеб', 'выпечка', 'кондитер', 'нан жасоочу'],
    'нан жасоочу': ['пекарь', 'повар', 'хлеб', 'выпечка'],
    'кондитер': ['повар', 'пекарь', 'торт', 'выпечка'],
    'горничная': ['уборщик', 'гостиница', 'отель', 'жайнакчы'],
    'жайнакчы': ['горничная', 'уборщик', 'гостиница', 'уборка'],
    'парикмахер': ['стрижка', 'салон', 'барбер', 'чач кескич', 'мастер'],
    'чач кескич': ['парикмахер', 'стрижка', 'салон', 'барбер'],
    'барбер': ['парикмахер', 'стрижка', 'борода', 'барбершоп'],
    'косметолог': ['красота', 'салон', 'уход', 'кожа', 'массаж'],
    'маникюр': ['мастер ногтей', 'педикюр', 'нейл', 'салон'],
    'визажист': ['макияж', 'красота', 'свадьба', 'косметолог'],
    'массажист': ['массаж', 'косметолог', 'реабилитация', 'спа'],
    'водитель': ['шофер', 'шофёр', 'доставка', 'курьер', 'логистика', 'таксист', 'айдоочу'],
    'айдоочу': ['водитель', 'шофер', 'доставка', 'таксист'],
    'таксист': ['водитель', 'такси', 'яндекс', 'айдоочу'],
    'курьер': ['доставка', 'водитель', 'логистика', 'жеткирүүчү'],
    'жеткирүүчү': ['курьер', 'доставка', 'водитель'],
    'логист': ['логистика', 'склад', 'доставка', 'экспедитор'],
    'кладовщик': ['склад', 'логистика', 'товар', 'учёт'],
    'строитель': ['прораб', 'строительство', 'ремонт', 'отделка', 'куруучу'],
    'куруучу': ['строитель', 'строительство', 'ремонт'],
    'прораб': ['строитель', 'строительство', 'ремонт', 'бригадир'],
    'сварщик': ['сварка', 'металл', 'строительство', 'завод'],
    'электрик': ['электричество', 'монтаж', 'проводка', 'ремонт'],
    'сантехник': ['водопровод', 'канализация', 'ремонт', 'трубы'],
    'каменщик': ['строитель', 'кладка', 'кирпич', 'строительство'],
    'плиточник': ['ремонт', 'плитка', 'отделка', 'строительство'],
    'маляр': ['краска', 'ремонт', 'отделка', 'стены'],
    'плотник': ['дерево', 'мебель', 'строительство', 'столяр'],
    'столяр': ['дерево', 'мебель', 'плотник', 'производство'],
    'архитектор': ['проект', 'строительство', 'дизайн', 'чертеж'],
    'врач': ['доктор', 'медицина', 'дарыгер', 'терапевт', 'хирург', 'педиатр'],
    'дарыгер': ['врач', 'доктор', 'медицина', 'терапевт'],
    'медсестра': ['медицина', 'больница', 'клиника', 'медик', 'медбрат'],
    'фельдшер': ['медицина', 'скорая', 'медсестра'],
    'фармацевт': ['аптека', 'медицина', 'лекарства', 'провизор'],
    'стоматолог': ['зубной', 'стоматология', 'врач', 'дантист'],
    'педиатр': ['детский врач', 'медицина', 'дети', 'доктор'],
    'акушер': ['роддом', 'беременность', 'медицина', 'врач'],
    'учитель': ['преподаватель', 'репетитор', 'педагог', 'мугалим', 'воспитатель'],
    'мугалим': ['учитель', 'преподаватель', 'педагог'],
    'преподаватель': ['учитель', 'репетитор', 'педагог', 'профессор'],
    'репетитор': ['учитель', 'преподаватель', 'педагог', 'обучение'],
    'воспитатель': ['детский сад', 'педагог', 'учитель', 'няня', 'балдар бакчасы'],
    'балдар бакчасы': ['воспитатель', 'детский сад', 'педагог'],
    'тренер': ['спорт', 'тренировка', 'фитнес', 'учитель', 'инструктор'],
    'инструктор': ['тренер', 'учитель', 'обучение', 'спорт'],
    'бухгалтер': ['бухгалтерия', 'финансы', '1с', 'учёт', 'учет', 'эсепчи'],
    'эсепчи': ['бухгалтер', 'финансы', 'учёт'],
    'финансист': ['бухгалтер', 'финансы', 'экономист', 'банк'],
    'экономист': ['бухгалтер', 'финансы', 'финансист', 'экономика'],
    'кредитный специалист': ['банк', 'кредит', 'финансы', 'займ', 'мкк'],
    'аудитор': ['бухгалтер', 'проверка', 'финансы', 'учёт'],
    'менеджер': ['управляющий', 'руководитель', 'администратор', 'директор', 'башчы'],
    'башчы': ['менеджер', 'руководитель', 'директор'],
    'администратор': ['менеджер', 'управляющий', 'офис', 'ресепшн', 'секретарь'],
    'директор': ['руководитель', 'менеджер', 'управляющий', 'начальник'],
    'секретарь': ['офис', 'администратор', 'делопроизводитель', 'помощник'],
    'hr': ['кадры', 'персонал', 'рекрутер', 'хр', 'кадровик'],
    'кадровик': ['hr', 'кадры', 'персонал', 'рекрутер'],
    'юрист': ['адвокат', 'право', 'юридический', 'нотариус'],
    'адвокат': ['юрист', 'право', 'защитник'],
    'нотариус': ['юрист', 'документы', 'право'],
    'охранник': ['охрана', 'секьюрити', 'безопасность', 'кайтаруучу', 'сторож'],
    'кайтаруучу': ['охранник', 'охрана', 'безопасность', 'сторож'],
    'сторож': ['охранник', 'охрана', 'безопасность', 'вахтер'],
    'агроном': ['сельское хозяйство', 'фермер', 'поле', 'урожай'],
    'фермер': ['сельское хозяйство', 'агроном', 'скот', 'поле', 'дыйкан'],
    'дыйкан': ['фермер', 'сельское хозяйство', 'поле', 'урожай'],
    'чабан': ['пастух', 'скот', 'овца', 'животноводство', 'малчы'],
    'малчы': ['чабан', 'пастух', 'скот', 'животноводство'],
    'ветеринар': ['животные', 'скот', 'ветеринария', 'зоотехник'],
    'механик': ['ремонт', 'завод', 'машина', 'автомеханик', 'слесарь'],
    'автомеханик': ['механик', 'ремонт', 'машина', 'автосервис', 'СТО'],
    'слесарь': ['механик', 'металл', 'ремонт', 'завод'],
    'грузчик': ['склад', 'погрузка', 'физический труд', 'жүк ташуучу'],
    'жүк ташуучу': ['грузчик', 'склад', 'погрузка'],
    'разнорабочий': ['рабочий', 'физический труд', 'стройка'],
    'гид': ['туризм', 'экскурсовод', 'путешествие', 'туроператор'],
    'экскурсовод': ['гид', 'туризм', 'путешествие', 'музей'],
    'уборщик': ['клининг', 'уборка', 'чистота', 'жайнакчы', 'дворник'],
    'дворник': ['уборщик', 'улица', 'уборка', 'двор'],
    'психолог': ['консультация', 'психология', 'помощь', 'терапевт'],
    'социальный работник': ['соцработник', 'помощь', 'социальная защита'],
}


def get_search_terms(query):
    q = query.lower().strip()
    terms = set(transliterate(q))
    for key, synonyms in SYNONYMS.items():
        if key in q or q in key:
            terms.update(synonyms)
            terms.add(key)
        for syn in synonyms:
            if syn in q or q in syn:
                terms.update(synonyms)
                terms.add(key)
    return list(terms)


def job_list_view(request):
    jobs = Job.objects.filter(is_active=True).order_by('-is_featured', '-created_at')
    search_query = request.GET.get('q', '').strip()
    current_category = request.GET.get('category', '')
    current_employment = request.GET.get('employment_type', '')
    current_experience = request.GET.get('experience', '')
    current_location = request.GET.get('location', '')

    if search_query:
        terms = get_search_terms(search_query)
        q_filter = Q()
        for term in terms:
            q_filter |= (
                Q(title__icontains=term) |
                Q(company__icontains=term) |
                Q(description__icontains=term) |
                Q(responsibilities__icontains=term) |
                Q(requirements__icontains=term)
            )
        jobs = jobs.filter(q_filter).distinct()

    if current_category:
        jobs = jobs.filter(category__slug=current_category)
    if current_employment:
        jobs = jobs.filter(employment_type=current_employment)
    if current_experience:
        jobs = jobs.filter(experience=current_experience)
    if current_location:
        jobs = jobs.filter(location=current_location)

    total_found = jobs.count()
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/job_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'current_category': current_category,
        'current_employment': current_employment,
        'current_experience': current_experience,
        'current_location': current_location,
        'total_found': total_found,
        'employment_choices': Job.EMPLOYMENT_CHOICES,
        'experience_choices': Job.EXPERIENCE_CHOICES,
        'city_choices': Job.CITY_CHOICES,
    })


def job_detail_view(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    Job.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    job.refresh_from_db()
    related_jobs = Job.objects.filter(
        is_active=True, category=job.category
    ).exclude(pk=pk).order_by('-created_at')[:4]
    already_applied = False
    if request.user.is_authenticated:
        already_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
    return render(request, 'core/job_detail.html', {
        'job': job,
        'related_jobs': related_jobs,
        'already_applied': already_applied,
    })


@login_required
def apply_job_view(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'Вы уже откликались на эту вакансию.' if request.session.get('lang') != 'ky' else 'Сиз бул жумушка мурунтан өтүндүңүз.')
        return redirect('core:job_detail', pk=pk)
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')
        JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
        )
        messages.success(request, 'Отклик отправлен!' if request.session.get('lang') != 'ky' else 'Өтүнүч жөнөтүлдү!')
        return redirect('core:job_detail', pk=pk)
    return render(request, 'core/apply_job.html', {'job': job})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = request.POST.get('role', 'seeker')
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            login(request, user)
            pending_job = request.session.pop('pending_job', None)
            if pending_job:
                profile.role = 'employer'
                profile.save()
                job_form = JobPostForm(pending_job)
                if job_form.is_valid():
                    job = job_form.save(commit=False)
                    job.author = user
                    job.is_active = False
                    job.status = 'pending'
                    job.save()
                    try:
                        from .telegram_bot import send_telegram
                        send_telegram(job)
                    except Exception as e:
                        logger.error(f'register send_telegram error: {e}')
                    return redirect('core:job_pending')
                else:
                    messages.warning(request, 'Аккаунт создан. Проверьте данные вакансии и опубликуйте снова.')
                    return redirect('core:post_job')
            messages.success(request, 'Добро пожаловать! Аккаунт успешно создан.')
            return redirect('core:profile')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:profile')
    form_errors = False
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', '')
            safe_next = next_url if next_url.startswith('/') and not next_url.startswith('//') else ''
            return redirect(safe_next or 'core:profile')
        else:
            form_errors = True
    return render(request, 'core/login.html', {'form': type('F', (), {'errors': form_errors})()})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Вы вышли из аккаунта.')
    return redirect('core:home')


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        profile.phone = request.POST.get('phone', '')
        profile.city = request.POST.get('city', '')
        profile.bio = request.POST.get('bio', '')
        profile.company_name = request.POST.get('company_name', '')
        profile.role = request.POST.get('role', profile.role)
        profile.save()
        messages.success(request, 'Профиль обновлён.')
        return redirect('core:profile')
    my_jobs = Job.objects.filter(author=request.user).order_by('-created_at') if profile.role == 'employer' else []
    my_applications = JobApplication.objects.filter(applicant=request.user).select_related('job').order_by('-created_at') if profile.role == 'seeker' else []
    return render(request, 'core/profile.html', {
        'profile': profile,
        'my_jobs': my_jobs,
        'my_applications': my_applications,
    })


def post_job(request):
    initial_data = request.session.pop('pending_job', None)
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            if not request.user.is_authenticated:
                request.session['pending_job'] = request.POST.dict()
                messages.info(request, 'Данные сохранены. Зарегистрируйтесь чтобы опубликовать вакансию.')
                return redirect('core:register')
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if profile.role != 'employer':
                profile.role = 'employer'
                profile.save()
            job = form.save(commit=False)
            job.author = request.user
            job.is_active = False
            job.status = 'pending'
            job.save()
            try:
                from .telegram_bot import send_telegram
                send_telegram(job)
            except Exception as e:
                logger.error(f'post_job send_telegram error: {e}')
            return redirect('core:job_pending')
        else:
            messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = JobPostForm(initial=initial_data)
    return render(request, 'core/post_job.html', {'form': form})


def job_pending_view(request):
    return render(request, 'core/job_pending.html')


@login_required
def delete_job(request, pk):
    job = get_object_or_404(Job, pk=pk, author=request.user)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Вакансия удалена.')
    return redirect('core:profile')


def support_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, 'Заполните все поля.')
            return render(request, 'core/support.html')

        ticket = SupportTicket.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=name,
            email=email,
            message=message,
        )

        try:
            from .telegram_bot import send_support_notify
            send_support_notify(ticket)
        except Exception as e:
            logger.error(f'support_view send_support_notify error: {e}')

        messages.success(request, 'Ваше обращение отправлено! Мы свяжемся с вами.')
        return redirect('core:support')

    return render(request, 'core/support.html')


def set_lang(request):
    lang = request.GET.get('lang', 'ru')
    if lang in ('ru', 'ky'):
        request.session['lang'] = lang
    return redirect(request.META.get('HTTP_REFERER', '/'))