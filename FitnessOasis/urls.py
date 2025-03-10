from django.contrib import admin
from django.urls import path
from myapp.views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homepage, name='homepage'),
    path('fadmin/', fadmin, name='fadmin'),
    path('faqs', faqs, name='faqs'),
    path('about', about, name='about'),
    path('testimonials', testimonials, name='testimonials'),
    path('contact', contact, name='contact'),
    path('login', user_login, name="login"),
    path('register', register, name="register"),
    path('profile', profile , name='profile'),
    path('logout', logout_view, name='logout'),
    path('fadmin', fadmin, name='fadmin'),
    path('admin_login', admin_login, name='admin_login'),
    path('admin_logout', admin_logout, name='admin_logout'),
    path('services', services, name='services'),
    path('book', book, name='book'),
    path('get_trainers/<int:service_id>/',get_trainers, name='get_trainers')


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
