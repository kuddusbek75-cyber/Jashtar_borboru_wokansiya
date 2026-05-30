from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Job, UserProfile


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'city', 'phone']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'employment_type', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'employment_type', 'experience', 'category', 'location']
    search_fields = ['title', 'company']
    list_editable = ['is_active', 'is_featured']
    readonly_fields = ['created_at', 'updated_at']

    def salary_range(self, obj):
        return obj.get_salary_display()
    salary_range.short_description = 'Зарплата'


admin.site.site_header = 'Жаштар Борбору — Администрация'
admin.site.site_title = 'Жаштар Борбору'
admin.site.index_title = 'Управление порталом'