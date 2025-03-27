from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db import models 
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from .models import Profile, Service, Trainer, Booking, Contact
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from decimal import Decimal, ROUND_HALF_UP
import requests
import base64
import uuid
import hmac
import hashlib
import requests
import json
import os
import logging
from django.db.models import Sum, Count


# Constants for eSewa integration
ESEWA_MERCHANT_CODE = "9806800001/2/3/4/5"  # Replace with your eSewa merchant code
ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"  # Replace with your eSewa secret key
ESEWA_PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_SUCCESS_URL = "http://localhost:8000/success"  # Replace with your success URL
ESEWA_FAILURE_URL = "http://localhost:8000/failure"  # Replace with your failure URL

def generate_signature(secret_key, message):
    """
    Generate a base64-encoded HMAC-SHA256 signature for eSewa.
    """
    secret_key = secret_key.encode('utf-8')
    message = message.encode('utf-8')
    signature = hmac.new(secret_key, message, hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')


# View to confirm order and generate eSewa payment form
@login_required
def confirm_order(request, booking_id):
    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        transaction_uuid = str(uuid.uuid4())

        # Store the transaction_uuid in the booking
        booking.transaction_uuid = transaction_uuid
        booking.save()

        # Cast total_amount to integer (eSewa expects no decimals)
        total_amount = int(Decimal(booking.price).quantize(Decimal('1.'), rounding=ROUND_HALF_UP))

        # Generate the message with strict formatting (no spaces)
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code=EPAYTEST"
        signature = generate_signature(ESEWA_SECRET_KEY, message)

        return render(request, 'booking_confirmation.html', {
            'booking': booking,
            'transaction_uuid': transaction_uuid,
            'total_amount': total_amount,
            'signature': signature,
            'merchant_code': ESEWA_MERCHANT_CODE,
            'success_url': ESEWA_SUCCESS_URL,
            'failure_url': ESEWA_FAILURE_URL,
        })

    except Exception as e:
        # Add error logging and proper message handling
        print(f"Error in confirm_order: {str(e)}")  # Log the error for debugging
        messages.error(request, f"Error confirming your order: {str(e)}")
        return redirect('homepage')

# View to handle eSewa payment success response
logger = logging.getLogger(__name__)
def success(request):
    try:
        logger.info(f"User session key: {request.session.session_key}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")

        encoded_data = request.GET.get('data')
        if not encoded_data:
            return render(request, 'error.html', {'message': 'No payment data received.'})

        # Decode the base64 data
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_string = decoded_bytes.decode('utf-8')

        # Parse the decoded string as JSON
        response_data = json.loads(decoded_string)

        # Extract all fields from the response
        transaction_code = response_data.get('transaction_code')
        status = response_data.get('status')
        total_amount = response_data.get('total_amount')
        transaction_uuid = response_data.get('transaction_uuid')
        product_code = response_data.get('product_code')
        signed_field_names = response_data.get('signed_field_names')
        signature = response_data.get('signature')

        # Construct the message using ALL signed fields in the correct order
        message = (
            f"transaction_code={transaction_code},"
            f"status={status},"
            f"total_amount={total_amount},"
            f"transaction_uuid={transaction_uuid},"
            f"product_code={product_code},"
            f"signed_field_names={signed_field_names}"
        )

        # Generate the expected signature
        expected_signature = generate_signature(ESEWA_SECRET_KEY, message)

        if signature == expected_signature:
            # Find the booking using the transaction_uuid
            booking = get_object_or_404(Booking, transaction_uuid=transaction_uuid)

            # Update the paid field to True
            if not booking.paid:
                booking.paid = True
                booking.save()
                messages.success(request, "Payment successful! Your booking is now confirmed.")
            else:
                messages.warning(request, "This booking is already paid.")

            # Keep the user logged in
            update_session_auth_hash(request, request.user)

            return render(request, 'success.html', {
                'message': 'Payment successful!',
                'booking': booking
            })
        else:
            return render(request, 'error.html', {'message': 'Invalid payment signature.'})
    except Exception as e:
        logger.error(f"Error in success view: {str(e)}")
        return render(request, 'error.html', {'message': f"An error occurred: {str(e)}" })
    
# View to handle eSewa payment failure
def failure(request):
    return render(request, 'failure.html', {'message': 'Payment failed or was canceled.'})

# View to book a service and generate eSewa payment
@login_required
def book(request):
    services = Service.objects.all().order_by('name')
    trainers = []
    preselected_service = None

    # Get service name from URL parameter
    service_name = request.GET.get('service')
    if service_name:
        try:
            # Case-insensitive match for service name
            preselected_service = Service.objects.get(name__iexact=service_name)
            # Get trainers for preselected service
            trainers = Trainer.objects.filter(service=preselected_service)
        except Service.DoesNotExist:
            messages.warning(request, f"Service '{service_name}' not found")

    # Package mapping remains the same
    package_mapping = {
        '1': 30, '3': 90, '6': 180, '12': 360
    }

    if request.method == 'POST':
        try:
            service_id = request.POST.get('service')
            trainer_id = request.POST.get('trainer')
            package_value = request.POST.get('package')
            start_date = request.POST.get('start_date')
            time_slot = request.POST.get('time_slot')  # Get selected time slot

            service = Service.objects.get(id=service_id)
            trainer = Trainer.objects.get(id=trainer_id)
            duration = package_mapping.get(package_value, 30)
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=duration)
            price = trainer.daily_rate * duration

            # Check if the time slot is already booked for the selected trainer and date range
            conflicting_bookings = Booking.objects.filter(
                trainer=trainer,
                start_date__lte=end_date_obj,
                end_date__gte=start_date_obj,
                time_slot=time_slot
            )
            if conflicting_bookings.exists():
                messages.error(request, f"The {time_slot} slot is already booked for the selected dates.")
                return redirect('book')

            # Create the booking
            booking = Booking.objects.create(
                user=request.user,
                service=service,
                trainer=trainer,
                start_date=start_date_obj,
                end_date=end_date_obj,
                time_slot=time_slot,  # Save the selected time slot
                price=price
            )

            # Update the trainer's booked_time_slots
            current_date = start_date_obj
            while current_date <= end_date_obj:
                trainer.booked_time_slots.append({
                    "date": current_date.isoformat(),
                    "time_slot": time_slot
                })
                current_date += timedelta(days=1)
            trainer.save()

            messages.success(request, "Booking created successfully!")
            # Fix: Redirect to confirm_order with the booking ID
            return redirect('confirm_order', booking_id=booking.id)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('book')

    return render(request, 'book.html', {
        'services': services,
        'trainers': trainers,
        'preselected_service': preselected_service
    })

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
            return "Set your preferences to get your personalized meal plans"
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
            return "Set your preferences to get personalized workout"
    return "General workout plans for beginners."

def generate_hydration_plan(profile):
    if profile and profile.weight:
        water_intake = profile.weight * 0.033  # Calculate daily water intake based on weight (in liters)
        return f"Stay hydrated! Your daily water intake: {water_intake:.2f} liters."
    return "Please update your profile with your weight to get a personalized hydration plan."

def get_users_with_similar_goals(current_user):
    current_goal = current_user.profile.fitness_goal
    return Profile.objects.filter(fitness_goal=current_goal).exclude(user=current_user)

def get_recommended_services(current_user, limit=1):
    similar_users = get_users_with_similar_goals(current_user)
    similar_user_ids = [profile.user.id for profile in similar_users]
    
    return (
        Booking.objects
        .filter(user__id__in=similar_user_ids, paid=True)
        .select_related('service', 'trainer')
        .order_by('-start_date')[:limit]
    )

# Keep only one version of homepage view
def homepage(request):
    profile = None
    recommended_bookings = []
    
    try:
        if request.user.is_authenticated:
            profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        pass

    if profile:
        meal_plan = generate_meal_plan(profile)
        workout_plan = generate_workout_plan(profile)
        hydration_plan = generate_hydration_plan(profile)
        recommended_bookings = get_recommended_services(request.user)
    else:
        meal_plan = workout_plan = hydration_plan = None

    return render(request, 'homepage.html', {
        'profile': profile,
        'meal_plan': meal_plan,
        'workout_plan': workout_plan,
        'hydration_plan': hydration_plan,
        'recommended_bookings': recommended_bookings,  # Match template variable name
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

def faqs(request):
    return render(request, 'faqs.html')

def testimonials(request):
    return render(request, 'testimonials.html')

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        Contact.objects.create(name=name, email=email, message=message)

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

# views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            # Redirect to the 'next' URL if it exists, otherwise redirect to 'homepage'
            next_url = request.GET.get('next', 'homepage')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'login.html')


@login_required
def profile(request):
    profile = request.user.profile
    bookings = Booking.objects.filter(user=request.user).order_by('-start_date')  # Fetch user's bookings
    print(bookings)

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
    
    print(f"Number of bookings: {bookings.count()}")

    return render(request, 'profile.html', {
        'profile': profile,
        'bookings': bookings
        })

def logout_view(request):
    logout(request)
    return redirect('homepage')

def services(request):
    return render(request, 'services.html')


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
    selected_date = request.GET.get('date')  # Get selected date from query parameters
    trainers = Trainer.objects.filter(service_id=service_id)
    trainer_data = []

    for trainer in trainers:
        # Check if the trainer is booked for the selected date (if provided)
        is_booked = False
        if selected_date:
            selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            is_booked = Booking.objects.filter(
                trainer=trainer,
                start_date__lte=selected_date_obj,
                end_date__gte=selected_date_obj
            ).exists()

        trainer_data.append({
            'id': trainer.id,
            'name': trainer.name,
            'experience': trainer.experience,
            'available_time_slots': trainer.available_time_slots,
            'is_booked': is_booked,  # Include booking status for the selected date
        })

    return JsonResponse({'trainers': trainer_data})

def get_available_slots(request, trainer_id):
    try:
        selected_date = request.GET.get('date')
        if not selected_date:
            return JsonResponse({'error': 'Date is required'}, status=400)

        # Parse date with error handling
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        # Get trainer with error handling
        try:
            trainer = Trainer.objects.get(id=trainer_id)
        except Trainer.DoesNotExist:
            return JsonResponse({'error': 'Trainer not found'}, status=404)

        # Get all booked slots for the selected date
        booked_slots = Booking.objects.filter(
            trainer=trainer,
            start_date__lte=selected_date,
            end_date__gte=selected_date
        ).values_list('time_slot', flat=True)

        # Get available slots by excluding booked slots
        available_slots = [slot for slot in trainer.available_time_slots if slot not in booked_slots]

        return JsonResponse({'available_slots': available_slots})

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_available_slots: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

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
                    daily_rate=daily_rate,
                    available_time_slots=selected_time_slots,
                    booked_time_slots=[]  # Initialize as empty list
                )
                messages.success(request, f"Trainer {trainer_name} added successfully!")
            except Service.DoesNotExist:
                messages.error(request, "Selected service does not exist.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

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

    # Calculate revenue, bookings, and average per booking for each service
    service_data = Booking.objects.filter(paid=True).values('service__name').annotate(
        total_revenue=Sum('price'),
        total_bookings=Count('id'),
        average_per_booking=Sum('price') / Count('id')
    )

    # Prepare data for each service
    service_revenue_data = {service['service__name']: service for service in service_data}

    # Fetch data for the dashboard
    services = Service.objects.all()
    trainers = Trainer.objects.all()
    available_trainers = Trainer.objects.count()
    total_bookings = Booking.objects.count()
    paid_bookings = Booking.objects.filter(paid=True)
    total_revenue = paid_bookings.aggregate(Sum('price'))['price__sum'] or 0
    
    # Calculate slots
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_week = now - timedelta(days=now.weekday())
    
    slots_per_month = Booking.objects.filter(start_date__gte=start_of_month).count()
    slots_per_week = Booking.objects.filter(start_date__gte=start_of_week).count()
    
    total_members = User.objects.count()
    contact_messages = Contact.objects.all().order_by('-created_at')

    return render(request, 'fadmin.html', {
        'services': services,
        'trainers': trainers,
        'available_trainers': available_trainers,
        'total_bookings': total_bookings,
        'paid_bookings': paid_bookings,
        'total_revenue': total_revenue,
        'slots_per_month': slots_per_month,
        'slots_per_week': slots_per_week,
        'total_members': total_members,
        'contact_messages': contact_messages,
        'service_revenue_data': service_revenue_data,  # Pass the calculated revenue data
    })


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

@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
def delete_trainer(request, trainer_id):
    try:
        trainer = Trainer.objects.get(id=trainer_id)
        trainer.delete()
        messages.success(request, f"Trainer {trainer.name} has been deleted successfully!")
    except Trainer.DoesNotExist:
        messages.error(request, "Trainer not found!")
    return redirect('fadmin')