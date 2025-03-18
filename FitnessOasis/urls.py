from django.contrib import admin
from django.urls import path
from myapp.views import (
    homepage, fadmin, faqs, about, testimonials, contact, 
    user_login, register, profile, logout_view, admin_login, 
    admin_logout, services, book, get_trainers, get_available_slots, 
    trainers, bmi, meal_plan_detail, workout_plan_detail, 
    confirm_order, delete_trainer, success, failure  # Add delete_trainer here
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homepage, name='homepage'),
    path('fadmin/', fadmin, name='fadmin'),
    path('faqs/', faqs, name='faqs'),
    path('about/', about, name='about'),
    path('testimonials/', testimonials, name='testimonials'),
    path('contact/', contact, name='contact'),
    path('login/', user_login, name="login"),
    path('register/', register, name="register"),
    path('profile/', profile, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('admin_login/', admin_login, name='admin_login'),
    path('admin_logout/', admin_logout, name='admin_logout'),
    path('services/', services, name='services'),
    path('book/', book, name='book'),
    path('get_trainers/<int:service_id>/', get_trainers, name='get_trainers'),
    path('get_available_slots/<int:trainer_id>/', get_available_slots, name='get_available_slots'),
    path('trainers/', trainers, name="trainers"),
    path('bmi/', bmi, name='bmi'),
    path('meal_plan/', meal_plan_detail, name='meal_plan_detail'),
    path('workout_plan/', workout_plan_detail, name='workout_plan_detail'),
    path('confirm_order/<int:booking_id>/', confirm_order, name='confirm_order'),
    path('delete_trainer/<int:trainer_id>/', delete_trainer, name='delete_trainer'),
    path('success/', success, name='esewa_success'),
    path('failure/', failure, name='esewa_failure')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
