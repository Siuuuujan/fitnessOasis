from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta, date
import os

def profile_picture_path(instance, filename):
    """Generate a file path for a new profile picture."""
    return f'profile_pics/{instance.user.username}/{filename}'

from django.db import models
from datetime import date
import os

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

    # Fitness goal choices
    FITNESS_GOAL_CHOICES = [
        ('Weight Gain', 'Weight Gain'),
        ('Weight Loss', 'Weight Loss'),
        ('Self Defense', 'Self Defense'),
        ('Strength', 'Strength'),
    ]
    fitness_goal = models.CharField(
        max_length=20,
        choices=FITNESS_GOAL_CHOICES,
        null=True,
        blank=True
    )

    # Fitness level choices
    FITNESS_LEVEL_CHOICES = [
        ('Novice', 'Novice'),
        ('Amateur', 'Amateur'),
        ('Expert', 'Expert'),
    ]
    fitness_level = models.CharField(
        max_length=10,
        choices=FITNESS_LEVEL_CHOICES,
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


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration_in_days = models.PositiveIntegerField(default=30)  # Default duration for the service
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Default price

    def __str__(self):
        return self.name

class Trainer(models.Model):
    name = models.CharField(max_length=100)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    experience = models.TextField()
    available_time_slots = models.JSONField(default=list)  # E.g., ["morning", "afternoon", "evening"]
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # New field for trainer's rate per day

    def __str__(self):
        return self.name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.service.duration_in_days)
        if not self.price:
            self.price = self.service.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - {self.service.name} ({self.start_date} to {self.end_date})'
