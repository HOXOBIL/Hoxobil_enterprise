from django.contrib import admin
from .models import Product, Order, OrderItem, WinningCode, CompetitionAttempt, SiteEvent, UserProfile # Added UserProfile
from django.utils.html import format_html
import json 

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
    list_display = ('id', 'user_display_name', 'total_amount', 'paid', 'paystack_reference', 'created_at')
    list_filter = ('paid', 'created_at', 'user')
    search_fields = ('id', 'email', 'paystack_reference', 'first_name', 'last_name', 'user__username')
    readonly_fields = ('paystack_reference', 'created_at', 'updated_at', 'total_amount', 'user') 
    
    class OrderItemInline(admin.TabularInline): 
        model = OrderItem
        readonly_fields = ('product_title', 'variant_title', 'quantity', 'price_at_purchase') 
        extra = 0 
        can_delete = False 

    inlines = [OrderItemInline]

    @admin.display(description='Customer')
    def user_display_name(self, obj):
        if obj.user:
            return obj.user.username
        return obj.email # Fallback to email if no user linked

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')
    list_filter = ('order__created_at',) 
    search_fields = ('product_title', 'variant_title', 'order__email', 'order__id', 'order__user__username')
    readonly_fields = ('order', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')

    @admin.display(description='Order')
    def order_link(self, obj):
        from django.urls import reverse
        link = reverse("admin:shop_order_change", args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)


@admin.register(WinningCode)
class WinningCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'prize_description', 'is_claimed', 'claimed_by_user_display', 'claimed_at', 'created_at')
    list_filter = ('is_claimed', 'created_at', 'claimed_by_user')
    search_fields = ('code', 'prize_description', 'claimed_by_user__username') 
    actions = ['mark_as_unclaimed']
    raw_id_fields = ('claimed_by_user',) 

    def mark_as_unclaimed(self, request, queryset):
        queryset.update(is_claimed=False, claimed_by_user=None, claimed_at=None)
    mark_as_unclaimed.short_description = "Mark selected codes as unclaimed"

    @admin.display(description='Claimed By User')
    def claimed_by_user_display(self, obj):
        return obj.claimed_by_user.username if obj.claimed_by_user else "-"


@admin.register(CompetitionAttempt)
class CompetitionAttemptAdmin(admin.ModelAdmin):
    list_display = ('submitted_code', 'user_display', 'session_key', 'ip_address', 'is_winner', 'attempted_at', 'winning_code_matched_link')
    list_filter = ('is_winner', 'attempted_at', 'user')
    search_fields = ('submitted_code', 'session_key', 'ip_address', 'user__username')
    readonly_fields = ('attempted_at', 'winning_code_matched', 'user', 'session_key', 'ip_address') 
    raw_id_fields = ('user', 'winning_code_matched')

    @admin.display(description='User')
    def user_display(self, obj):
        return obj.user.username if obj.user else (obj.session_key or "Anonymous")
    
    @admin.display(description='Matched Winning Code')
    def winning_code_matched_link(self, obj):
        from django.urls import reverse
        if obj.winning_code_matched:
            link = reverse("admin:shop_winningcode_change", args=[obj.winning_code_matched.id])
            return format_html('<a href="{}">{}</a>', link, obj.winning_code_matched.code)
        return "-"

@admin.register(SiteEvent)
class SiteEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'event_datetime', 'is_active', 'updated_at')
    list_filter = ('is_active', 'event_name')
    search_fields = ('event_name', 'notes')

# +++ NEW: UserProfile Admin Registration +++
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'referral_code', 'referred_by_username', 'referral_count', 'unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at')
    search_fields = ('user__username', 'referral_code', 'referred_by__username')
    list_filter = ('referral_count', 'unlocked_first_digit')
    readonly_fields = ('referral_code', 'referral_count', 'unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'referred_by', 'unlocked_digit_from_code') # Makes user selection easier

    @admin.display(description='User')
    def user_username(self, obj):
        return obj.user.username

    @admin.display(description='Referred By')
    def referred_by_username(self, obj):
        return obj.referred_by.username if obj.referred_by else "-"

    fieldsets = (
        (None, {'fields': ('user', 'referral_code')}),
        ('Referral Stats', {'fields': ('referred_by', 'referral_count')}),
        ('Competition Reward', {'fields': ('unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)})
    )
