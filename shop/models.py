from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# +++ Custom User Manager +++
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a Superuser with the given email and password.
        """
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
    """
    Custom User model using email as the unique identifier.
    """
    email = models.EmailField(unique=True, help_text="Your primary email address, used for login.")
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.')
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Returns the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email # Fallback to email if no name is set

    def get_short_name(self):
        """Returns the short name for the user."""
        return self.first_name

# Product Model (Adjusted for customizer)
class Product(models.Model):
    """
    Represents a product synced from Printify, which can also be customized.
    """
    printify_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique Product ID from Printify. This is for synced products.")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    base_price_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Base display price in NGN.")
    primary_image_url = models.URLField(max_length=1024, blank=True, null=True, help_text="URL of the primary display image.")
    product_options_data = models.JSONField(default=list, blank=True, help_text="Structured product options (e.g., Color, Size) from Printify.")
    variants_data = models.JSONField(default=list, blank=True, help_text="Detailed list of all product variants with their properties.")
    tags = models.JSONField(default=list, blank=True, help_text="Tags associated with the product from Printify.")
    printify_shop_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Printify Shop ID this product belongs to.")
    printify_blueprint_id = models.IntegerField(blank=True, null=True, help_text="Printify Blueprint ID for this product type.")
    printify_print_provider_id = models.IntegerField(blank=True, null=True, help_text="Printify Print Provider ID associated with this product.")
    is_published = models.BooleanField(default=True, help_text="Is the product published on Printify?")
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last sync from Printify.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # NEW: Add a field for the mockup image for customization
    mockup_image = models.ImageField(upload_to='product_mockups/', blank=True, null=True,
                                     help_text="Base image for the product customizer (e.g., blank T-shirt, mug).")

    class Meta:
        ordering = ['title']
        verbose_name = "Synced Product"
        verbose_name_plural = "Synced Products"

    def __str__(self):
        return f"{self.title} (ID: {self.printify_id})"

# +++ Custom Design Model +++
class CustomDesign(models.Model):
    """
    Stores a user's custom design created using the product customizer.
    This design can then be added to an OrderItem.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who created the design (optional).")
    # Link to the base Product model that represents the type of item being customized
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='custom_designs', help_text="The base product type this design is for (e.g., T-Shirt, Hoodie).")
    
    # The actual rendered image of the custom design from the canvas
    design_image = models.ImageField(upload_to='custom_designs/%Y/%m/%d/', help_text="Rendered PNG image of the custom design.")
    
    # Optional: Store Fabric.js JSON for re-editing or detailed processing
    design_json = models.JSONField(null=True, blank=True, help_text="Fabric.js JSON representation of the design for future editing.")
    
    # Selected options from the frontend that describe the desired final product
    selected_product_type = models.CharField(max_length=100, help_text="e.g., T-Shirt, Hoodie, Mug - from frontend selection.")
    selected_size = models.CharField(max_length=50, help_text="e.g., S, M, L, XL - from frontend selection.")
    selected_color = models.CharField(max_length=50, help_text="e.g., White, Black, Navy - from frontend selection.")

    created_at = models.DateTimeField(auto_now_add=True)
    
    # Printify related fields
    printify_image_id = models.CharField(max_length=100, blank=True, null=True, help_text="Printify asset ID for the uploaded design image.")
    # This ID would be used if you decide to create a unique Printify product for each custom design.
    # More commonly, you'd use printify_image_id in an order line item for an existing Printify product.
    printify_product_id = models.CharField(max_length=100, blank=True, null=True, help_text="Printify product ID if a unique product was created for this design.")
    
    # Status to track processing (e.g., in cart, uploaded to Printify, order placed)
    status = models.CharField(
        max_length=50,
        default='pending',
        choices=[
            ('pending', 'Pending Processing'),
            ('uploaded_to_printify', 'Image Uploaded to Printify'),
            ('printify_product_ready', 'Printify Product Ready (Draft)'), # If you create a draft product
            ('added_to_cart', 'Added to User Cart'), # Important for your next step
            ('order_created', 'Order Created on Printify'),
            ('fulfilled', 'Fulfilled by Printify'),
            ('failed', 'Failed to Process')
        ],
        help_text="Current processing status of the custom design."
    )

    class Meta:
        verbose_name = "Custom Design"
        verbose_name_plural = "Custom Designs"
        ordering = ['-created_at']

    def __str__(self):
        user_info = self.user.email if self.user else 'Guest'
        return f"Custom Design for {self.product.title} ({self.selected_size}, {self.selected_color}) by {user_info} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    

# Order Models
class Order(models.Model):
    """
    Represents a customer order in the shop.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who placed the order, if authenticated.")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="Nigeria")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    paystack_reference = models.CharField(max_length=100, blank=True, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        user_identifier = self.user.email if self.user else self.email
        return f"Order {self.id} by {user_identifier}"

class OrderItem(models.Model):
    """
    Represents a single item within an order, which can be a standard product
    or a custom-designed product.
    """
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Link to the base Product model
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items', help_text="The base product ordered.")
    # New: Link to CustomDesign if this order item is a custom product
    custom_design = models.OneToOneField(CustomDesign, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='order_item', # Ensures easy lookup from CustomDesign to OrderItem
                                         help_text="If this is a customized product, link to its design.")
    
    product_title = models.CharField(max_length=200, help_text="Redundant but useful for displaying name if product is deleted or custom_design is null.")
    variant_title = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., 'Large, Black' for a T-shirt.")
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Store the actual Printify variant ID if this order item corresponds to a specific Printify variant
    printify_variant_id = models.CharField(max_length=100, blank=True, null=True, help_text="Printify variant ID of the purchased item.")

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        if self.custom_design:
            return f"{self.quantity} x Custom Design for {self.custom_design.product.title} in Order {self.order.id}"
        return f"{self.quantity} x {self.product_title} ({self.variant_title or 'N/A'}) in Order {self.order.id}"
    
    def get_cost(self):
        return self.price_at_purchase * self.quantity


# UserProfile MODEL FOR REFERRALS
class UserProfile(models.Model):
    """
    Extends the CustomUser model with referral-specific information.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True, help_text="User's unique referral code.")
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_made', help_text="The user who referred this profile.")
    referral_count = models.PositiveIntegerField(default=0, help_text="Number of successful referrals made by this user.")
    unlocked_first_digit = models.CharField(max_length=1, blank=True, null=True, help_text="The first digit of a winning code unlocked via referrals.")
    unlocked_digit_from_code = models.ForeignKey('WinningCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='digit_revealed_for', help_text="The winning code from which the digit was revealed.")
    digit_unlocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile for {self.user.email}"

    def generate_referral_code(self):
        """Generates a unique 8-character uppercase hexadecimal referral code."""
        if not self.referral_code:
            while True:
                code = uuid.uuid4().hex[:8].upper()
                if not UserProfile.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        return self.referral_code

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.generate_referral_code()
        super().save(*args, **kwargs)

# Signal to create or update UserProfile when User instance is saved
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to ensure a UserProfile is created or updated
    whenever a CustomUser instance is saved.
    """
    if created:
        UserProfile.objects.create(user=instance)
    # This `get_or_create` pattern is more robust for cases where
    # `instance.profile` might not exist (e.g., initial superuser creation)
    # or to handle potential race conditions.
    else:
        try:
            instance.profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)


# Competition Models
class WinningCode(models.Model):
    """
    Represents a secret winning code for a competition.
    """
    code = models.CharField(max_length=6, unique=True, help_text="The 6-digit winning code.")
    prize_description = models.CharField(max_length=255, help_text="Description of the prize for this code.")
    is_claimed = models.BooleanField(default=False, help_text="Has this prize been claimed?")
    claimed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who claimed this prize.")
    claimed_at = models.DateTimeField(blank=True, null=True, help_text="When this prize was claimed.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Winning Code"
        verbose_name_plural = "Winning Codes"

    def __str__(self):
        claimed_status = f"Claimed by {self.claimed_by_user.email} at {self.claimed_at.strftime('%Y-%m-%d %H:%M')}" if self.claimed_by_user and self.claimed_at else "Unclaimed"
        return f"{self.code} - Prize: {self.prize_description} ({claimed_status})"

class CompetitionAttempt(models.Model):
    """
    Records each attempt by a user (or anonymous session) to guess a winning code.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who made the attempt, if authenticated.")
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True, help_text="User's session key if attempt was anonymous.")
    ip_address = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    submitted_code = models.CharField(max_length=6, help_text="The code submitted by the user.")
    is_winner = models.BooleanField(default=False, help_text="Was this attempt a winning one?")
    winning_code_matched = models.ForeignKey(WinningCode, on_delete=models.SET_NULL, null=True, blank=True, help_text="Which winning code was matched, if any.")
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Competition Attempt"
        verbose_name_plural = "Competition Attempts"
        ordering = ['-attempted_at']

    def __str__(self):
        identifier = self.user.email if self.user else (self.session_key or self.ip_address or "Anonymous")
        status = "WINNER" if self.is_winner else "Loser"
        return f"Attempt '{self.submitted_code}' by {identifier} ({status}) at {self.attempted_at.strftime('%Y-%m-%d %H:%M')}"

# Site Event Model
class SiteEvent(models.Model):
    """
    Stores key dates and times for site-wide events, such as launch dates.
    """
    EVENT_NAME_CHOICES = [
        ('SITE_LAUNCH', 'Site Launch Date/Time'),
        # Add other event types as needed, e.g., 'REFERRAL_BONUS_END'
    ]
    event_name = models.CharField(max_length=50, choices=EVENT_NAME_CHOICES, unique=True, help_text="The unique name of the event.")
    event_datetime = models.DateTimeField(help_text="The date and time of the event.")
    is_active = models.BooleanField(default=True, help_text="Is this event currently active/relevant?")
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this event.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Event"
        verbose_name_plural = "Site Events"
        ordering = ['-event_datetime']

    def __str__(self):
        return f"{self.get_event_name_display()} - {self.event_datetime.strftime('%Y-%m-%d %H:%M %Z')}"