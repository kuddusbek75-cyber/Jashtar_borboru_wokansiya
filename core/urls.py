from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('vacancies/', views.job_list_view, name='job_list'),
    path('vacancies/<int:pk>/', views.job_detail_view, name='job_detail'),
    path('vacancies/<int:pk>/apply/', views.apply_job_view, name='apply_job'),
    path('vacancies/<int:pk>/delete/', views.delete_job, name='delete_job'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('post-job/', views.post_job, name='post_job'),
    path('job-pending/', views.job_pending_view, name='job_pending'),
    path('set-lang/', views.set_lang, name='set_lang'),
    path('support/', views.support_view, name='support'),
]