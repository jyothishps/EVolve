from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Single User model for both Driver and Admin.
    Role field decide permission level. No separate Admin/Driver table.
    """

    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('DRIVER', 'Driver'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='DRIVER')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_admin(self):
        return self.role == 'ADMIN'

    def is_driver(self):
        return self.role == 'DRIVER'

    def __str__(self):
        return f"{self.username} ({self.role})"