from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from .models import Profile, Service, Trainer, Booking  # Package model no longer used
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta

def homepage(request):
    return render(request, 'homepage.html')

def faqs(request):
    return render(request, 'faqs.html')

def testimonials(request):
    return render(request, 'testimonials.html')

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")
        # You can save this data to a database or send an email
        return HttpResponse("Message sent successfully!")
    return render(request, "contact.html")

def about(request):
    return render(request, 'about.html')

def register(request):
    if request.method == "POST":
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        
        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('register')
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=firstname,
            last_name=lastname
        )
        user.save()
        
        Profile.objects.create(user=user)
        auth_login(request, user)
        messages.success(request, "Registration successful! You are now logged in.")
        return redirect('homepage')
    return render(request, 'register.html')

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('homepage')
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'login.html')

@login_required
def profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile.age = request.POST.get('age', profile.age)
            profile.height = request.POST.get('height', profile.height)
            profile.weight = request.POST.get('weight', profile.weight)
            profile.gender = request.POST.get('gender', profile.gender)
            profile.goals = request.POST.get('goals', profile.goals)
            if request.FILES.get('profile_picture'):
                profile.profile_picture = request.FILES.get('profile_picture')
            if profile.age and profile.height and profile.weight:
                try:
                    profile.age = int(profile.age)
                    profile.height = float(profile.height)
                    profile.weight = float(profile.weight)
                    if profile.age <= 0 or profile.height <= 0 or profile.weight <= 0:
                        raise ValueError("Age, height, and weight must be positive values.")
                    valid_genders = ["Male", "Female", "Other"]
                    if profile.gender not in valid_genders:
                        raise ValueError("Invalid gender selected.")
                    profile.save()
                    messages.success(request, "Profile updated successfully!")
                except ValueError as e:
                    messages.error(request, f"Error: {e}")
                except Exception as e:
                    messages.error(request, f"Error: {e}")
            else:
                messages.error(request, "Please fill in all required fields.")
        elif 'update_security' in request.POST:
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect!")
                return redirect('profile')
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match!")
                return redirect('profile')
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated successfully!")
        return redirect('profile')
    return render(request, 'profile.html', {'profile': profile})

def logout_view(request):
    logout(request)
    return redirect('homepage')

def services(request):
    return render(request, 'services.html')

def book(request):
    services = Service.objects.all()
    trainers = []

    # Define package mapping: key is package option value and value is duration in days.
    package_mapping = {
        '1': 30,
        '3': 90,
        '6': 180,
        '12': 360,
    }

    if request.method == 'POST':
        service_id = request.POST.get('service')
        trainer_id = request.POST.get('trainer')
        package_value = request.POST.get('package')  # "1", "3", "6", "12"
        start_date = request.POST.get('start_date')
        
        service = Service.objects.get(id=service_id)
        trainer = Trainer.objects.get(id=trainer_id)

        duration = package_mapping.get(package_value, 30)
        end_date = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration)

        # Calculate price using trainer's daily_rate
        price = trainer.daily_rate * duration

        booking = Booking.objects.create(
            user=request.user,
            service=service,
            trainer=trainer,
            start_date=start_date,
            end_date=end_date,
            price=price
        )
        
        return render(request, 'booking_confirmation.html', {'booking': booking})
    
    return render(request, 'book.html', {'services': services, 'trainers': trainers})


def get_trainers(request, service_id):
    trainers = Trainer.objects.filter(service_id=service_id)
    trainer_data = [{
        'id': trainer.id,
        'name': trainer.name,
        'experience': trainer.experience,
        'available_time_slots': trainer.available_time_slots,
    } for trainer in trainers]
    return JsonResponse({'trainers': trainer_data})



def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def fadmin(request):
    if request.method == 'POST':
        if 'add_trainer' in request.POST:
            trainer_name = request.POST.get('trainer-name')
            service_id = request.POST.get('service')
            experience = request.POST.get('experience')
            daily_rate = request.POST.get('daily_rate')
            selected_time_slots = request.POST.getlist('time_slots')
            
            if not trainer_name or not service_id or not experience or not daily_rate or not selected_time_slots:
                messages.error(request, "All fields are required!")
                return redirect('fadmin')
            
            try:
                service = Service.objects.get(id=service_id)
                trainer = Trainer.objects.create(
                    name=trainer_name,
                    service=service,
                    experience=experience,
                    daily_rate=daily_rate
                )
                trainer.available_time_slots = selected_time_slots
                trainer.save()
                messages.success(request, f"Trainer {trainer_name} added with time slots!")
            except Service.DoesNotExist:
                messages.error(request, "Selected service does not exist.")
        elif 'add_service' in request.POST:
            service_name = request.POST.get('service-name')
            if not service_name:
                messages.error(request, "Service name is required!")
            elif Service.objects.filter(name=service_name).exists():
                messages.error(request, "Service already exists!")
            else:
                Service.objects.create(name=service_name)
                messages.success(request, f"Service '{service_name}' added successfully!")
        return redirect('fadmin')

    services = Service.objects.all()
    available_trainers = Trainer.objects.count()
    return render(request, 'fadmin.html', {'services': services, 'available_trainers': available_trainers})

@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('fadmin')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect('fadmin')
        else:
            messages.error(request, "Invalid admin credentials.")
    response = render(request, 'admin_login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')
