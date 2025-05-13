from django.db import models
from django.conf import settings # To link to the User model
import uuid 
from django.utils import timezone # For default datetime

# Product Model
class Product(models.Model):
    """
    Stores product information, largely synced from Printify.
    """
    printify_id = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Unique Product ID from Printify."
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    base_price_ngn = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Base display price in NGN (e.g., price of the default or first available variant)."
    )
    primary_image_url = models.URLField(
        max_length=1024, 
        blank=True, 
        null=True,
        help_text="URL of the primary display image."
    )
    
    # Stores the structured options for the product as provided by Printify.
    # Example: [{'name': 'Color', 'type': 'dropdown', 'values': [{'id': '101', 'title': 'Red'}, ...]}, ...]
    product_options_data = models.JSONField(
        default=list, 
        blank=True,
        help_text="Structured product options (e.g., Color, Size) from Printify, including option value IDs."
    )
    
    # Stores a list of all variants for this product.
    # Each item in the list is a dictionary representing a variant.
    # Example variant dict: {
    #   'id': 'printify_variant_id', 
    #   'title': 'Red / Small', 
    #   'price_ngn': 2500.00, # Price of this specific variant in NGN
    #   'sku': 'SKU123', 
    #   'is_enabled': True, 
    #   'is_available': True, # Printify's stock/availability status for this variant
    #   'option_value_ids': ['101', '201'] # List of Printify option value IDs that define this variant
    # }
    variants_data = models.JSONField(
        default=list, 
        blank=True,
        help_text="Detailed list of all product variants with their properties, prices, and defining option value IDs."
    )

    tags = models.JSONField(default=list, blank=True, help_text="Tags associated with the product from Printify.")
    printify_shop_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Printify Shop ID this product belongs to.")
    printify_blueprint_id = models.IntegerField(blank=True, null=True, help_text="Printify Blueprint ID.")
    printify_print_provider_id = models.IntegerField(blank=True, null=True, help_text="Printify Print Provider ID.")

    is_published = models.BooleanField(default=True, help_text="Is the product published on Printify?")
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last sync from Printify.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} (Printify ID: {self.printify_id})"

    class Meta:
        ordering = ['title']
        verbose_name = "Synced Product"
        verbose_name_plural = "Synced Products"

# Order Models
class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        help_text="User who placed the order, if authenticated."
    )
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

    def __str__(self):
        user_identifier = self.user.username if self.user else self.email
        return f"Order {self.id} by {user_identifier}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_title = models.CharField(max_length=200)
    variant_title = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) 
    
    def __str__(self):
        return f"{self.quantity} x {self.product_title} ({self.variant_title or 'N/A'}) in Order {self.order.id}"

    def get_cost(self):
        return self.price_at_purchase * self.quantity

# Competition Models
class WinningCode(models.Model):
    code = models.CharField(max_length=6, unique=True, help_text="The 6-digit winning code.")
    prize_description = models.CharField(max_length=255, help_text="Description of the prize for this code.")
    is_claimed = models.BooleanField(default=False, help_text="Has this prize been claimed?")
    claimed_by_identifier = models.CharField(max_length=255, blank=True, null=True, 
                                             help_text="Identifier of the winner (e.g., email or session key).")
    claimed_at = models.DateTimeField(blank=True, null=True, help_text="When this prize was claimed.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - Prize: {self.prize_description} (Claimed: {self.is_claimed})"

    class Meta:
        verbose_name = "Winning Code"
        verbose_name_plural = "Winning Codes"

class CompetitionAttempt(models.Model):
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True, 
                                   help_text="User's session key for anonymous tracking.")
    ip_address = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    submitted_code = models.CharField(max_length=6, help_text="The code submitted by the user.")
    is_winner = models.BooleanField(default=False, help_text="Was this attempt a winning one?")
    winning_code_matched = models.ForeignKey(WinningCode, on_delete=models.SET_NULL, null=True, blank=True,
                                             help_text="Which winning code was matched, if any.")
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        identifier = self.session_key or self.ip_address or "Unknown"
        return f"Attempt: {self.submitted_code} by {identifier} at {self.attempted_at} (Winner: {self.is_winner})"

    class Meta:
        verbose_name = "Competition Attempt"
        verbose_name_plural = "Competition Attempts"
        ordering = ['-attempted_at']

# Site Event Model (for launch date, etc.)
class SiteEvent(models.Model):
    EVENT_NAME_CHOICES = [
        ('SITE_LAUNCH', 'Site Launch Date/Time'),
        # Add other event types here if needed in the future
    ]
    event_name = models.CharField(
        max_length=50, 
        choices=EVENT_NAME_CHOICES, 
        unique=True, 
        help_text="The unique name of the event (e.g., Site Launch Date/Time)."
    )
    event_datetime = models.DateTimeField(
        help_text="The date and time of the event."
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Is this event currently active/relevant for display (e.g., for a countdown)?"
    )
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this event.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_event_name_display()} - {self.event_datetime.strftime('%Y-%m-%d %H:%M %Z')}"

    class Meta:
        verbose_name = "Site Event"
        verbose_name_plural = "Site Events"
        ordering = ['-event_datetime']
