from django.contrib import admin
from django.urls import reverse # Moved import to top
from django.utils.html import format_html
import json 
from .models import Product, Order, OrderItem, WinningCode, CompetitionAttempt, SiteEvent, UserProfile

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'printify_id', 
        'base_price_ngn', 
        'is_published', 
        'last_synced_at', 
        'created_at'
    )
    search_fields = ('title', 'printify_id', 'description', 'tags__icontains') 
    list_filter = ('is_published', 'last_synced_at', 'created_at', 'updated_at', 'printify_shop_id', 'printify_print_provider_id')
    
    readonly_fields = (
        'printify_id', 
        'last_synced_at', 
        'created_at', 
        'updated_at',
        'product_options_data_display', 
        'variants_data_display'       
    )
    
    fieldsets = (
        (None, {'fields': ('title', 'printify_id', 'description', 'primary_image_url', 'base_price_ngn', 'is_published')}),
        ('Printify Meta Data', {'classes': ('collapse',), 'fields': ('printify_shop_id', 'printify_blueprint_id', 'printify_print_provider_id', 'tags')}),
        ('Advanced Data (JSON)', {'classes': ('collapse',), 'fields': ('product_options_data_display', 'variants_data_display')}),
        ('Timestamps', {'classes': ('collapse',), 'fields': ('last_synced_at', 'created_at', 'updated_at')})
    )

    @admin.display(description='Product Options (JSON)')
    def product_options_data_display(self, obj):
        if obj.product_options_data:
            return format_html("<pre>{}</pre>", json.dumps(obj.product_options_data, indent=2))
        return "-"

    @admin.display(description='Variants Data (JSON)')
    def variants_data_display(self, obj):
        if obj.variants_data:
            return format_html("<pre>{}</pre>", json.dumps(obj.variants_data, indent=2))
        return "-"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_customer_identifier', 'total_amount', 'paid', 'paystack_reference', 'created_at') # Changed method name
    list_filter = ('paid', 'created_at', 'user')
    search_fields = ('id', 'email', 'paystack_reference', 'first_name', 'last_name', 'user__email') # Changed user__username
    readonly_fields = ('paystack_reference', 'created_at', 'updated_at', 'total_amount', 'user') 
    
    class OrderItemInline(admin.TabularInline): 
        model = OrderItem
        readonly_fields = ('product_title', 'variant_title', 'quantity', 'price_at_purchase') 
        extra = 0 
        can_delete = False 

    inlines = [OrderItemInline]

    @admin.display(description='Customer Email') # Updated description
    def get_customer_identifier(self, obj): # Renamed method
        if obj.user:
            return obj.user.email # Changed from obj.user.username
        return obj.email # Fallback to order's email if no user linked
    get_customer_identifier.admin_order_field = 'user__email' # Optional for sorting

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')
    list_filter = ('order__created_at',) 
    search_fields = ('product_title', 'variant_title', 'order__email', 'order__id', 'order__user__email') # Changed order__user__username
    readonly_fields = ('order', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')

    @admin.display(description='Order')
    def order_link(self, obj):
        link = reverse("admin:shop_order_change", args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)


@admin.register(WinningCode)
class WinningCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'prize_description', 'is_claimed', 'get_claimed_by_user_email', 'claimed_at', 'created_at') # Changed method name
    list_filter = ('is_claimed', 'created_at', 'claimed_by_user')
    search_fields = ('code', 'prize_description', 'claimed_by_user__email') # Changed claimed_by_user__username
    actions = ['mark_as_unclaimed']
    raw_id_fields = ('claimed_by_user',) 

    def mark_as_unclaimed(self, request, queryset):
        queryset.update(is_claimed=False, claimed_by_user=None, claimed_at=None)
    mark_as_unclaimed.short_description = "Mark selected codes as unclaimed"

    @admin.display(description='Claimed By Email') # Updated description
    def get_claimed_by_user_email(self, obj): # Renamed method
        return obj.claimed_by_user.email if obj.claimed_by_user else "-" # Changed from .username
    get_claimed_by_user_email.admin_order_field = 'claimed_by_user__email' # Optional for sorting


@admin.register(CompetitionAttempt)
class CompetitionAttemptAdmin(admin.ModelAdmin):
    list_display = ('submitted_code', 'get_user_identifier_for_attempt', 'session_key', 'ip_address', 'is_winner', 'attempted_at', 'winning_code_matched_link') # Changed method name
    list_filter = ('is_winner', 'attempted_at', 'user')
    search_fields = ('submitted_code', 'session_key', 'ip_address', 'user__email') # Changed user__username
    readonly_fields = ('attempted_at', 'winning_code_matched', 'user', 'session_key', 'ip_address') 
    raw_id_fields = ('user', 'winning_code_matched')

    @admin.display(description='User Email/Identifier') # Updated description
    def get_user_identifier_for_attempt(self, obj): # Renamed method
        return obj.user.email if obj.user else (obj.session_key or "Anonymous") # Changed from .username
    get_user_identifier_for_attempt.admin_order_field = 'user__email' # Optional for sorting
    
    @admin.display(description='Matched Winning Code')
    def winning_code_matched_link(self, obj):
        if obj.winning_code_matched:
            link = reverse("admin:shop_winningcode_change", args=[obj.winning_code_matched.id])
            return format_html('<a href="{}">{}</a>', link, obj.winning_code_matched.code)
        return "-"

@admin.register(SiteEvent)
class SiteEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'event_datetime', 'is_active', 'updated_at')
    list_filter = ('is_active', 'event_name')
    search_fields = ('event_name', 'notes')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_user_profile_email', 'referral_code', 'get_referred_by_profile_email', 'referral_count', 'unlocked_first_digit', 'digit_unlocked_at') # Updated method names and removed unlocked_digit_from_code as it's an object
    search_fields = ('user__email', 'referral_code', 'referred_by__email') # Changed user__username and referred_by__username
    list_filter = ('referral_count', 'unlocked_first_digit')
    readonly_fields = ('referral_code', 'referral_count', 'unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'referred_by', 'unlocked_digit_from_code')

    @admin.display(description='User Email')
    def get_user_profile_email(self, obj):
        if obj.user:
            return obj.user.email # Changed from obj.user.username
        return "-"
    get_user_profile_email.admin_order_field = 'user__email'

    @admin.display(description='Referred By Email')
    def get_referred_by_profile_email(self, obj):
        if obj.referred_by:
            return obj.referred_by.email # Changed from obj.referred_by.username
        return "-"
    get_referred_by_profile_email.admin_order_field = 'referred_by__email'

    fieldsets = (
        (None, {'fields': ('user', 'referral_code')}),
        ('Referral Stats', {'fields': ('referred_by', 'referral_count')}),
        ('Competition Reward', {'fields': ('unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)})
    )
