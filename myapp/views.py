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
from django.core.exceptions import ValidationError
import requests\



def generate_meal_plan(profile):
    if profile:
        if profile.fitness_goal == 'Weight Loss':
            return "Low-calorie, high-protein meal plans with lean meats, vegetables, and complex carbs to help you shed pounds while maintaining energy."
        elif profile.fitness_goal == 'Weight Gain':
            return "High-calorie meal plans packed with protein, healthy fats, and complex carbs to promote muscle growth and healthy weight gain."
        elif profile.fitness_goal == 'Self Defense':
            return "Balanced meal plans focused on agility, endurance, and strength. Includes lean proteins, healthy fats, and energy-boosting carbs."
        elif profile.fitness_goal == 'Strength':
            return "Power-building meal plans with high-protein foods, complex carbs, and healthy fats to enhance muscle growth and recovery."
        else:
            return "Well-balanced meal plans to support overall health and fitness."
    return "General meal plans to get you started."

def generate_workout_plan(profile):
    if profile:
        if profile.fitness_goal == 'Weight Loss':
            if profile.fitness_level == 'Novice':
                return "Beginner weight loss workout plans with moderate cardio and bodyweight exercises."
            elif profile.fitness_level == 'Amateur':
                return "Intermediate weight loss workout routines with HIIT and strength training."
            elif profile.fitness_level == 'Expert':
                return "Advanced weight loss routines focused on high-intensity interval training (HIIT) and strength training."
            else:
                return "General weight loss workout plans focused on cardio and strength training."
        
        elif profile.fitness_goal == 'Weight Gain':
            if profile.fitness_level == 'Novice':
                return "Beginner weight gain workout plans with compound movements and basic strength exercises."
            elif profile.fitness_level == 'Amateur':
                return "Intermediate weight gain workout routines with a mix of compound lifts and hypertrophy-focused exercises."
            elif profile.fitness_level == 'Expert':
                return "Advanced weight gain routines focused on strength training and progressive overload."
            else:
                return "General weight gain workout plans with a mix of compound lifts and high-rep exercises."
        
        elif profile.fitness_goal == 'Self Defense':
            if profile.fitness_level == 'Novice':
                return "Beginner self-defense workout plans with basic martial arts and core exercises."
            elif profile.fitness_level == 'Amateur':
                return "Intermediate self-defense workout routines with martial arts drills, bodyweight exercises, and agility work."
            elif profile.fitness_level == 'Expert':
                return "Advanced self-defense routines with martial arts sparring, strength, and conditioning."
            else:
                return "General self-defense workout plans with martial arts and strength-based training."
        
        elif profile.fitness_goal == 'Strength':
            if profile.fitness_level == 'Novice':
                return "Beginner strength workout plans with compound lifts and full-body workouts."
            elif profile.fitness_level == 'Amateur':
                return "Intermediate strength routines focused on progressive overload and major muscle groups."
            elif profile.fitness_level == 'Expert':
                return "Advanced strength routines with heavy lifting, powerlifting, and strength specialization."
            else:
                return "General strength workout plans with a focus on muscle growth and progressive overload."
        
        else:
            return "General workout plans for various fitness goals and levels."
    return "General workout plans for beginners."

def generate_hydration_plan(profile):
    if profile and profile.weight:
        water_intake = profile.weight * 0.033  # Calculate daily water intake based on weight (in liters)
        return f"Stay hydrated! Your daily water intake: {water_intake:.2f} liters."
    return "Please update your profile with your weight to get a personalized hydration plan."

from django.shortcuts import render
from .models import Profile

def homepage(request):
    # Get the user's profile if authenticated
    profile = Profile.objects.get(user=request.user) if request.user.is_authenticated else None

    # Check if the profile exists and has the necessary data for meal/workout/hydration plans
    if profile:
        meal_plan = generate_meal_plan(profile)
        workout_plan = generate_workout_plan(profile)
        hydration_plan = generate_hydration_plan(profile)
    else:
        meal_plan = None
        workout_plan = None
        hydration_plan = None
    
    # Pass these plans to the template
    return render(request, 'homepage.html', {
        'profile': profile,
        'meal_plan': meal_plan,
        'workout_plan': workout_plan,
        'hydration_plan': hydration_plan,
    })

API_KEY = "6769c288e7784defaf9cd89214732996"

def fetch_full_meal_plan(profile):
    """Fetch a detailed meal plan from Spoonacular API based on user profile."""
    if not profile:
        return {"error": "Please complete your profile to get a personalized meal plan."}

    fitness_goal_calories = {
        "Weight Loss": 1800,
        "Weight Gain": 3000,
        "Self Defense": 2500,
        "Strength": 2800
    }
    
    target_calories = fitness_goal_calories.get(profile.fitness_goal, 2200)

    # Fetch meal plan from Spoonacular API
    api_url = f"https://api.spoonacular.com/mealplanner/generate?timeFrame=day&targetCalories={target_calories}&apiKey={API_KEY}"
    
    response = requests.get(api_url)
    
    if response.status_code == 200:
        return response.json()  # Returns full meal plan as JSON
    else:
        return {"error": "Failed to fetch meal plan from Spoonacular."}

def meal_plan_detail(request):
    """Renders meal plan details page."""
    profile = Profile.objects.get(user=request.user) if request.user.is_authenticated else None
    meal_plan = fetch_full_meal_plan(profile) if profile else None
    
    return render(request, 'meal_plan.html', {'meal_plan': meal_plan})

import requests

import json
import os

def fetch_workout_plan(profile):
    if profile:
        goal = profile.fitness_goal  # e.g., "Weight Loss", "Weight Gain"
        level = profile.fitness_level  # e.g., "Novice", "Amateur", "Expert"

        # Load workout plans from the JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'static', 'workout_plans.json')

        try:
            with open(json_path, 'r') as file:
                workout_plans = json.load(file)
        except FileNotFoundError:
            return {"error": "Workout plans file not found."}
        except json.JSONDecodeError:
            return {"error": "Error decoding JSON file."}

        # Retrieve the specific workout plan
        if goal in workout_plans and level in workout_plans[goal]:
            return workout_plans[goal][level]
        else:
            return workout_plans["Default"]  # Return a general plan if not found

    return {"error": "Please complete your profile."}

    
from django.shortcuts import render
from .models import Profile

def workout_plan_detail(request):
    profile = Profile.objects.get(user=request.user) if request.user.is_authenticated else None
    print(f"Profile Found: {profile}")  # Debugging

    if profile:
        workout_plan = fetch_workout_plan(profile)
        print(f"Generated Plan: {workout_plan}")  # Debugging
    else:
        workout_plan = {"error": "No workout plan available."}

    return render(request, 'workout_plan.html', {'workout_plan': workout_plan})


def hydration_plan_detail(request):
    # Get the user's profile if authenticated
    profile = Profile.objects.get(user=request.user) if request.user.is_authenticated else None

    # Fetch full hydration plan for the authenticated user
    if profile:
        hydration_plan = generate_hydration_plan(profile)
    else:
        hydration_plan = None

    return render(request, 'hydration_plan.html', {'hydration_plan': hydration_plan})


# View for the homepage
def homepage(request):
    profile = Profile.objects.get(user=request.user) if request.user.is_authenticated else None
    
    if profile:
        # Generate dynamic recommendations based on the user's profile
        meal_plan = generate_meal_plan(profile)
        workout_plan = generate_workout_plan(profile)
        hydration_plan = generate_hydration_plan(profile)
    else:
        # Provide default messages if the profile is empty
        meal_plan = "Please complete your profile to get personalized meal plans."
        workout_plan = "Please complete your profile to get personalized workout plans."
        hydration_plan = "Please complete your profile to get personalized hydration plans."
    
    return render(request, 'homepage.html', {
        'profile': profile,
        'meal_plan': meal_plan,
        'workout_plan': workout_plan,
        'hydration_plan': hydration_plan,
    })

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
            
            # Handling new fitness goal and fitness level
            profile.fitness_goal = request.POST.get('fitness_goal', profile.fitness_goal)
            profile.fitness_level = request.POST.get('fitness_level', profile.fitness_level)
            
            if request.FILES.get('profile_picture'):
                profile.profile_picture = request.FILES.get('profile_picture')
                
            # Validate the data
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

                    valid_fitness_goals = ["Weight Gain", "Weight Loss", "Self Defense", "Strength"]
                    if profile.fitness_goal not in valid_fitness_goals:
                        raise ValueError("Invalid fitness goal selected.")
                    
                    valid_fitness_levels = ["Novice", "Amateur", "Expert"]
                    if profile.fitness_level not in valid_fitness_levels:
                        raise ValueError("Invalid fitness level selected.")
                    
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

def trainers(request):
    trainers = Trainer.objects.all()
    return render(request, 'trainers.html', {'trainers': trainers})

@login_required
def bmi(request):
    profile = request.user.profile
    bmi = None
    classification = None
    ideal_weight = None

    if request.method == 'POST':
        # Get the data from the POST request (without updating the profile)
        weight = request.POST.get('weight')
        height = request.POST.get('height')

        try:
            # Validate and calculate BMI if weight and height are provided
            if weight and height:
                weight = float(weight)
                height = float(height)

                # Calculate BMI
                height_in_meters = height / 100  # Convert height to meters
                bmi = weight / (height_in_meters ** 2)

                # Classify BMI
                if bmi < 18.5:
                    classification = "Underweight"
                elif 18.5 <= bmi < 24.9:
                    classification = "Normal weight"
                elif 25 <= bmi < 29.9:
                    classification = "Overweight"
                else:
                    classification = "Obese"

                # Calculate ideal weight (for BMI = 22)
                ideal_weight = 22 * (height_in_meters ** 2)

        except ValueError:
            # Handle invalid weight or height input
            pass

    return render(request, 'bmi.html', {
        'profile': profile,
        'bmi': bmi,
        'classification': classification,
        'ideal_weight': ideal_weight
    })


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
