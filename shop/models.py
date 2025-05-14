from django.db import models
from django.conf import settings 
import uuid 
from django.utils import timezone 
from django.db.models.signals import post_save 
from django.dispatch import receiver
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# +++ Custom User Manager +++
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

# +++ Custom User Model +++
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, help_text="Your primary email address, used for login.")
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.')
    is_active = models.BooleanField(default=True, help_text=('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(default=timezone.now)
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'; REQUIRED_FIELDS = ['first_name', 'last_name']
    def __str__(self): return self.email
    def get_full_name(self): return f"{self.first_name} {self.last_name}".strip()
    def get_short_name(self): return self.first_name
    class Meta: verbose_name = 'User'; verbose_name_plural = 'Users'

# Product Model
class Product(models.Model):
    printify_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique Product ID from Printify.")
    title = models.CharField(max_length=255); description = models.TextField(blank=True, null=True)
    base_price_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Base display price in NGN.")
    primary_image_url = models.URLField(max_length=1024, blank=True, null=True, help_text="URL of the primary display image.")
    product_options_data = models.JSONField(default=list, blank=True, help_text="Structured product options (e.g., Color, Size) from Printify.")
    variants_data = models.JSONField(default=list, blank=True, help_text="Detailed list of all product variants with their properties.")
    tags = models.JSONField(default=list, blank=True, help_text="Tags associated with the product from Printify.")
    printify_shop_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Printify Shop ID this product belongs to.")
    printify_blueprint_id = models.IntegerField(blank=True, null=True, help_text="Printify Blueprint ID.")
    printify_print_provider_id = models.IntegerField(blank=True, null=True, help_text="Printify Print Provider ID.")
    is_published = models.BooleanField(default=True, help_text="Is the product published on Printify?")
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last sync from Printify.")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.title} (ID: {self.printify_id})"
    class Meta: ordering = ['title']; verbose_name = "Synced Product"; verbose_name_plural = "Synced Products"

# Order Models
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who placed the order, if authenticated.")
    first_name = models.CharField(max_length=100); last_name = models.CharField(max_length=100, blank=True) 
    email = models.EmailField(); phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255); city = models.CharField(max_length=100)
    state = models.CharField(max_length=100); zipcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="Nigeria")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2); paid = models.BooleanField(default=False)
    paystack_reference = models.CharField(max_length=100, blank=True, unique=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ('-created_at',); 
    def __str__(self): user_identifier = self.user.email if self.user else self.email; return f"Order {self.id} by {user_identifier}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_title = models.CharField(max_length=200); variant_title = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1); price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) 
    def __str__(self): return f"{self.quantity} x {self.product_title} ({self.variant_title or 'N/A'}) in Order {self.order.id}"
    def get_cost(self): return self.price_at_purchase * self.quantity

# UserProfile MODEL FOR REFERRALS
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True, help_text="User's unique referral code.")
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_made', help_text="The user who referred this profile.")
    referral_count = models.PositiveIntegerField(default=0, help_text="Number of successful referrals made by this user.")
    unlocked_first_digit = models.CharField(max_length=1, blank=True, null=True, help_text="The first digit of a winning code unlocked via referrals.")
    unlocked_digit_from_code = models.ForeignKey('WinningCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='digit_revealed_for', help_text="The winning code from which the digit was revealed.")
    digit_unlocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.email}"

    def generate_referral_code(self):
        # This method generates a unique referral code.
        # The 'if not self.referral_code:' check ensures it only runs if no code exists.
        if not self.referral_code:
            # The 'while True:' loop continues until a unique code is found.
            while True: 
                code = uuid.uuid4().hex[:8].upper() # Generates a potential code.
                # This 'if' checks if the generated code is already in use.
                if not UserProfile.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break # *** THIS BREAK IS CORRECTLY INDENTED INSIDE THE 'if' AND 'while' ***
        return self.referral_code

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.generate_referral_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

# Signal to create or update UserProfile when User instance is saved
@receiver(post_save, sender=settings.AUTH_USER_MODEL) 
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        # print(f"UserProfile created for {instance.email}") 
    try:
        instance.profile.save() # Ensure referral code is generated if not present on existing profiles too
        # print(f"UserProfile save called for {instance.email}") 
    except UserProfile.DoesNotExist:
         UserProfile.objects.create(user=instance) 
         # print(f"UserProfile created on demand for {instance.email} because it was missing.")


# Competition Models
class WinningCode(models.Model):
    code = models.CharField(max_length=6, unique=True, help_text="The 6-digit winning code.")
    prize_description = models.CharField(max_length=255, help_text="Description of the prize for this code.")
    is_claimed = models.BooleanField(default=False, help_text="Has this prize been claimed?")
    claimed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who claimed this prize.")
    claimed_at = models.DateTimeField(blank=True, null=True, help_text="When this prize was claimed.")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): claimed_status = f"Claimed by {self.claimed_by_user.email}" if self.claimed_by_user else "Unclaimed"; return f"{self.code} - Prize: {self.prize_description} ({claimed_status})"
    class Meta: verbose_name = "Winning Code"; verbose_name_plural = "Winning Codes"

class CompetitionAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who made the attempt, if authenticated.")
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True, help_text="User's session key if attempt was anonymous.")
    ip_address = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    submitted_code = models.CharField(max_length=6, help_text="The code submitted by the user.")
    is_winner = models.BooleanField(default=False, help_text="Was this attempt a winning one?")
    winning_code_matched = models.ForeignKey(WinningCode, on_delete=models.SET_NULL, null=True, blank=True, help_text="Which winning code was matched, if any.")
    attempted_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): identifier = self.user.email if self.user else (self.session_key or self.ip_address or "Unknown"); return f"Attempt: {self.submitted_code} by {identifier} at {self.attempted_at} (Winner: {self.is_winner})"
    class Meta: verbose_name = "Competition Attempt"; verbose_name_plural = "Competition Attempts"; ordering = ['-attempted_at']

# Site Event Model
class SiteEvent(models.Model):
    EVENT_NAME_CHOICES = [('SITE_LAUNCH', 'Site Launch Date/Time'),]
    event_name = models.CharField(max_length=50, choices=EVENT_NAME_CHOICES, unique=True, help_text="The unique name of the event.")
    event_datetime = models.DateTimeField(help_text="The date and time of the event.")
    is_active = models.BooleanField(default=True, help_text="Is this event currently active/relevant?")
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this event.")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.get_event_name_display()} - {self.event_datetime.strftime('%Y-%m-%d %H:%M %Z')}"
    class Meta: verbose_name = "Site Event"; verbose_name_plural = "Site Events"; ordering = ['-event_datetime']

