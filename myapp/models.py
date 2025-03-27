from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta, date
import os

def profile_picture_path(instance, filename):
    """Generate a file path for a new profile picture."""
    return f'profile_pics/{instance.user.username}/{filename}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to=profile_picture_path, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True, editable=False)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    goals = models.TextField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        null=True,
        blank=True
    )
    fitness_goal = models.CharField(
        max_length=20,
        choices=[('Weight Gain', 'Weight Gain'), ('Weight Loss', 'Weight Loss'), ('Self Defense', 'Self Defense'), ('Strength', 'Strength')],
        null=True,
        blank=True
    )
    fitness_level = models.CharField(
        max_length=10,
        choices=[('Novice', 'Novice'), ('Amateur', 'Amateur'), ('Expert', 'Expert')],
        null=True,
        blank=True
    )

    def calculate_age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def save(self, *args, **kwargs):
        if self.date_of_birth:
            self.age = self.calculate_age()
        try:
            old_profile = Profile.objects.get(id=self.id)
            if old_profile.profile_picture and old_profile.profile_picture != self.profile_picture:
                if os.path.isfile(old_profile.profile_picture.path):
                    os.remove(old_profile.profile_picture.path)
        except Profile.DoesNotExist:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} Profile'

class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration_in_days = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return self.name

class Trainer(models.Model):
    name = models.CharField(max_length=100)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    experience = models.TextField()
    available_time_slots = models.JSONField(default=list)
    booked_time_slots = models.JSONField(default=None)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)  # New field to check if the trainer is active

    def __str__(self):
        return self.name

class Booking(models.Model):
    TIME_SLOT_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    time_slot = models.CharField(
        max_length=20,
        choices=TIME_SLOT_CHOICES,
        default="morning"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    paid = models.BooleanField(default=False)
    transaction_uuid = models.CharField(max_length=36, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.service.duration_in_days)
        if not self.price:
            self.price = self.service.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - {self.service.name} ({self.start_date} to {self.end_date})'