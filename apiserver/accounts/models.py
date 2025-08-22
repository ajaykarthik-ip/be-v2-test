from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.designation = "Employee"  
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.designation = "Manager"  
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    DESIGNATION_CHOICES = [
        ('employee', 'Employee'),
        ('senior_employee', 'Senior Employee'),
        ('team_lead', 'Team Lead'),
        ('manager', 'Manager'),
        ('senior_manager', 'Senior Manager'),
        ('director', 'Director'),
    ]
    
    objects = UserManager()

    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Add designation field
    designation = models.CharField(
        max_length=50,
        choices=DESIGNATION_CHOICES,
        default='employee',
        help_text="User's designation in the company"
    )
    
    # Add company field for "Mobiux Employee"
    company = models.CharField(max_length=100, default="Mobiux", blank=True)

    active = models.BooleanField(default=True)
    staff = models.BooleanField(default=False)  # a admin user; non super-user
    admin = models.BooleanField(default=False)  # a superuser

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return f"{self.email}"
    
    def get_role_display(self):
        return f"{self.company} {self.get_designation_display()}"
    
    def get_designation_based_on_admin(self):
        if self.admin:
            return "Manager"
        return "Employee"

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.staff

    @property
    def is_admin(self):
        "Is the user a admin member?"
        return self.admin

    @property
    def is_active(self):
        "Is the user active?"
        return self.active