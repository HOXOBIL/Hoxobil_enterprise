from django.contrib import admin
from .models import Product, Order, OrderItem, WinningCode, CompetitionAttempt, SiteEvent
from django.utils.html import format_html
import json  # For pretty printing JSON in admin

# Inside shop/admin.py

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'printify_id', 
        'base_price_ngn', # This should be 'base_price_ngn', not 'price'
        'is_published', 
        'last_synced_at', 
        'created_at'
    )
    # ... rest of your ProductAdmin class ...
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
        (None, {
            'fields': ('title', 'printify_id', 'description', 'primary_image_url', 'base_price_ngn', 'is_published')
        }),
        ('Printify Meta Data', {
            'classes': ('collapse',),
            'fields': ('printify_shop_id', 'printify_blueprint_id', 'printify_print_provider_id', 'tags'),
        }),
        ('Advanced Data (View Only)', {
            'classes': ('collapse',),
            'fields': ('product_options_data_display', 'variants_data_display'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('last_synced_at', 'created_at', 'updated_at')
        })
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

# Register Order model
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'total_amount', 'paid', 'paystack_reference', 'created_at')
    list_filter = ('paid', 'created_at')
    search_fields = ('id', 'email', 'paystack_reference', 'first_name', 'last_name')
    readonly_fields = ('paystack_reference', 'created_at', 'updated_at', 'total_amount', 'user')

    class OrderItemInline(admin.TabularInline):
        model = OrderItem
        readonly_fields = ('product_title', 'variant_title', 'quantity', 'price_at_purchase')
        extra = 0
        can_delete = False

    inlines = [OrderItemInline]

# Register OrderItem model
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')
    list_filter = ('order__created_at',)
    search_fields = ('product_title', 'variant_title', 'order__email', 'order__id')
    readonly_fields = ('order', 'product_title', 'variant_title', 'quantity', 'price_at_purchase')

    @admin.display(description='Order')
    def order_link(self, obj):
        from django.urls import reverse
        link = reverse("admin:shop_order_change", args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)

# Register the Competition models
@admin.register(WinningCode)
class WinningCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'prize_description', 'is_claimed', 'claimed_by_identifier', 'claimed_at', 'created_at')
    list_filter = ('is_claimed', 'created_at')
    search_fields = ('code', 'prize_description', 'claimed_by_identifier')
    actions = ['mark_as_unclaimed']

    def mark_as_unclaimed(self, request, queryset):
        queryset.update(is_claimed=False, claimed_by_identifier=None, claimed_at=None)
    mark_as_unclaimed.short_description = "Mark selected codes as unclaimed"

@admin.register(CompetitionAttempt)
class CompetitionAttemptAdmin(admin.ModelAdmin):
    list_display = ('submitted_code', 'session_key', 'ip_address', 'is_winner', 'attempted_at', 'winning_code_matched_link')
    list_filter = ('is_winner', 'attempted_at')
    search_fields = ('submitted_code', 'session_key', 'ip_address')
    readonly_fields = ('attempted_at', 'winning_code_matched')

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
