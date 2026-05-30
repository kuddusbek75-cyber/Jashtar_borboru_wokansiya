from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, Job


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        label='Я регистрируюсь как',
        widget=forms.RadioSelect
    )
    first_name = forms.CharField(max_length=50, required=True, label='Имя')
    last_name = forms.CharField(max_length=50, required=True, label='Фамилия')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role']
            )
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=False, label='Имя')
    last_name = forms.CharField(max_length=50, required=False, label='Фамилия')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = UserProfile
        fields = ['phone', 'city', 'bio', 'company_name']
        labels = {
            'phone': 'Телефон',
            'city': 'Город',
            'bio': 'О себе',
            'company_name': 'Название организации',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email


class JobPostForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'category', 'location',
            'employment_type', 'experience',
            'salary_from', 'salary_to',
            'description', 'requirements', 'responsibilities',
            'contact_email', 'contact_phone',
        ]
        labels = {
            'title': 'Должность',
            'company': 'Организация',
            'category': 'Категория',
            'location': 'Город',
            'employment_type': 'Тип занятости',
            'experience': 'Опыт работы',
            'salary_from': 'Зарплата от (сом)',
            'salary_to': 'Зарплата до (сом)',
            'description': 'Описание вакансии',
            'requirements': 'Требования к кандидату',
            'responsibilities': 'Обязанности',
            'contact_email': 'Контактный email',
            'contact_phone': 'Контактный телефон',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'requirements': forms.Textarea(attrs={'rows': 5}),
            'responsibilities': forms.Textarea(attrs={'rows': 5}),
        }