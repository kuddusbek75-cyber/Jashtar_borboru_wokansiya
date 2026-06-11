# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [('seeker', 'Соискатель'), ('employer', 'Работодатель')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seeker')
    phone = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    company_name = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return self.user.username


class Job(models.Model):
    EMPLOYMENT_CHOICES = [
        ('full', 'Полная занятость'),
        ('part', 'Частичная занятость'),
        ('intern', 'Стажировка'),
        ('remote', 'Удалённая работа'),
    ]
    EXPERIENCE_CHOICES = [
        ('none', 'Без опыта'),
        ('1year', 'До 1 года'),
        ('3years', 'От 1 до 3 лет'),
        ('5years', 'От 3 до 5 лет'),
    ]
    CITY_CHOICES = [
        ('Бишкек', 'Бишкек'),
        ('Ош', 'Ош'),
        ('Джалал-Абад', 'Джалал-Абад'),
        ('Каракол', 'Каракол'),
        ('Токмок', 'Токмок'),
        ('Нарын', 'Нарын'),
        ('Талас', 'Талас'),
        ('Баткен', 'Баткен'),
        ('Кант', 'Кант'),
        ('Кара-Балта', 'Кара-Балта'),
        ('Узген', 'Узген'),
        ('Балыкчы', 'Балыкчы'),
        ('Чолпон-Ата', 'Чолпон-Ата'),
        ('Майлуу-Суу', 'Майлуу-Суу'),
        ('Сулюкта', 'Сулюкта'),
        ('Кок-Жангак', 'Кок-Жангак'),
        ('Кемин', 'Кемин'),
        ('Таш-Кумыр', 'Таш-Кумыр'),
        ('Удалённо', 'Удалённо'),
    ]
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    title = models.CharField(max_length=200, verbose_name='Должность')
    company = models.CharField(max_length=200, verbose_name='Организация')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    location = models.CharField(max_length=150, choices=CITY_CHOICES, default='Бишкек')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='full')
    experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='none')
    salary_from = models.PositiveIntegerField(null=True, blank=True)
    salary_to = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    responsibilities = models.TextField(blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    views_count = models.PositiveIntegerField(default=0, verbose_name='Просмотры')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f'{self.title} - {self.company}'

    def get_salary_display(self):
        if self.salary_from and self.salary_to:
            return f'{self.salary_from:,} - {self.salary_to:,} сом'
        elif self.salary_from:
            return f'от {self.salary_from:,} сом'
        elif self.salary_to:
            return f'до {self.salary_to:,} сом'
        return 'По договорённости'


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('viewed', 'Просмотрен'),
        ('accepted', 'Принят'),
        ('rejected', 'Отклонён'),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField(blank=True, verbose_name='Сопроводительное письмо')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f'{self.applicant.username} -> {self.job.title}'


class Payment(models.Model):
    TYPE_CHOICES = [
        ('publish', 'Публикация вакансии'),
        ('top', 'Поднять в топ'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Ожидает проверки'),
        ('approved', 'Подтверждена'),
        ('rejected', 'Отклонена'),
    ]
    BANK_CHOICES = [
        ('mbank', 'M-Bank'),
        ('obank', 'O!Bank'),
        ('optima', 'Optima Bank'),
        ('bakai', 'Бакай Банк'),
        ('demir', 'Демир Банк'),
        ('kompanion', 'Компаньон Банк'),
        ('aiyl', 'Айыл Банк'),
        ('kicb', 'KICB'),
        ('rsk', 'РСК Банк'),
        ('dos', 'Дос-Кредобанк'),
        ('elqr', 'ELQR'),
        ('other', 'Другой'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.PositiveIntegerField()
    check_image = models.ImageField(upload_to='payment_checks/', blank=True, null=True, verbose_name='Чек')
    sender_phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон отправителя')
    sender_name = models.CharField(max_length=100, blank=True, verbose_name='Имя отправителя')
    sender_bank = models.CharField(max_length=50, choices=BANK_CHOICES, blank=True, verbose_name='Банк')
    comment = models.CharField(max_length=500, blank=True, verbose_name='Комментарий')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.get_payment_type_display()} — {self.status}'


class SupportTicket(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    name = models.CharField(max_length=100, verbose_name='Имя')
    email = models.EmailField(verbose_name='Email')
    message = models.TextField(verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Обращение в поддержку'
        verbose_name_plural = 'Обращения в поддержку'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.created_at.strftime("%d.%m.%Y")}'