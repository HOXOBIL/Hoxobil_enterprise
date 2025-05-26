from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404, HttpResponseBadRequest
from django.urls import reverse
from .models import Product, Order, OrderItem, WinningCode, CompetitionAttempt, SiteEvent, UserProfile, CustomDesign
import requests
import os
import json
import uuid
from django.contrib import messages
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from django.contrib.auth.views import redirect_to_login
from .forms import CustomUserCreationForm, EmailAuthenticationForm
from .signals import process_successful_referral
from .printify import PrintifyAPI # Import your PrintifyAPI client
import base64 # For base64 encoding/decoding image data
from django.core.files.base import ContentFile
from django.template.defaultfilters import slugify # For generating clean filenames
import logging

logger = logging.getLogger(__name__)

# --- Configuration ---
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')
PRINTIFY_API_TOKEN = os.getenv("PRINTIFY_API_TOKEN")
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')

if not PRINTIFY_API_TOKEN: logger.warning("🔴 CRITICAL WARNING: PRINTIFY_API_TOKEN is not set.")
if not PAYSTACK_SECRET_KEY: logger.warning("🔴 CRITICAL WARNING: PAYSTACK_SECRET_KEY is not set.")
if not PRINTIFY_SHOP_ID: logger.warning("🔴 CRITICAL WARNING: PRINTIFY_SHOP_ID is not set.")

HEADERS = { 'Authorization': f'Bearer {PRINTIFY_API_TOKEN}', 'Content-Type': 'application/json'}
USD_TO_NGN_RATE = Decimal('1607.00') # Make sure this is up-to-date!
API_BASE_URL = "https://api.printify.com/v1"
PAYSTACK_API_BASE_URL = "https://api.paystack.co"

# Initialize Printify API client
printify_client = PrintifyAPI(api_key=PRINTIFY_API_TOKEN)


# --- Cart Helper Functions ---
def get_cart(request):
    cart = request.session.get('cart', {})
    return cart

def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

# --- Views ---
def home(request):
    return render(request, 'mystore/home.html')

def infer_category_from_title(title):
    title_lower = title.lower()
    if "hoodie" in title_lower or "hooded sweatshirt" in title_lower: return "Hoodies & Sweatshirts"
    if "t-shirt" in title_lower or "tee" in title_lower: return "T-Shirts"
    if "jogger" in title_lower or "sweatpants" in title_lower: return "Joggers & Sweatpants"
    if "tank top" in title_lower: return "Tank Tops"
    if "mug" in title_lower: return "Mugs"
    if "poster" in title_lower: return "Posters & Wall Art"
    return "Other"

def fetch_printify_products(request):
    if not PRINTIFY_API_TOKEN: messages.error(request, "API token not configured."); return render(request, 'mystore/products.html', {'categorized_products': {}, 'error': 'API token not configured.'})
    if not PRINTIFY_SHOP_ID: messages.error(request, "Shop ID not configured."); return render(request, 'mystore/products.html', {'categorized_products': {}, 'error': 'Shop ID not configured.'})
    api_url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products.json"
    categorized_products = defaultdict(list)
    error_message_for_template = None
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        raw_products = response.json().get('data', [])
        for item in raw_products:
            variants = item.get('variants', [])
            price_cents = variants[0].get('price', 0) if variants else 0
            price_ngn = (Decimal(price_cents) / Decimal('100.0')) * USD_TO_NGN_RATE
            img_url = item.get('images', [{}])[0].get('src', 'https://placehold.co/600x400?text=No+Image')
            product_title = item.get('title', 'No Title')
            category = infer_category_from_title(product_title)
            proc_variants = []
            for v_data in variants:
                v_price_cents = Decimal(v_data.get('price', 0))
                v_price_ngn = (v_price_cents / Decimal('100.0')) * USD_TO_NGN_RATE
                proc_variants.append({'id': str(v_data.get('id')), 'title': v_data.get('title', 'N/A'), 'price_ngn': float(v_price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'is_enabled': v_data.get('is_enabled', False), 'is_available': v_data.get('is_available', True), 'option_value_ids': [str(oid) for oid in v_data.get('options',[])] })
            product_item_data = {'id': str(item.get('id')), 'title': product_title, 'price': float(price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'image_url': img_url, 'variants': proc_variants, 'options': item.get('options', []) }
            categorized_products[category].append(product_item_data)
    except Exception as e:
        error_message_for_template = f"Error fetching products: {str(e)}"
        logger.error(f"❌ {error_message_for_template}")
        messages.error(request, "Could not fetch products.")
    return render(request, 'mystore/products.html', {'categorized_products': dict(categorized_products), 'error': error_message_for_template })

def product_detail(request, product_id):
    if not PRINTIFY_API_TOKEN or not PRINTIFY_SHOP_ID: messages.error(request, "API/Shop token not configured."); return render(request, 'mystore/product_detail.html', {'product': None, 'error': 'Configuration error.'})
    url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id}.json"
    product_data_for_template = None
    error_msg = None
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        item = res.json()
        opts = [{'name':o.get('name'),'type':o.get('type'),'values':[{'id':str(v.get('id')),'title':v.get('title')} for v in o.get('values',[])]} for o in item.get('options',[])]
        proc_vars = []
        for v_data in item.get('variants', []):
            v_price_ngn = (Decimal(v_data.get('price',0))/Decimal('100.0'))*USD_TO_NGN_RATE
            proc_vars.append({'id':str(v_data.get('id')),'title':v_data.get('title','N/A'), 'price_ngn':float(v_price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'is_enabled':v_data.get('is_enabled',False),'is_available':v_data.get('is_available',True), 'option_value_ids':[str(oid) for oid in v_data.get('options',[])]})
        base_price = proc_vars[0]['price_ngn'] if proc_vars else 0.0
        
        # Look up the local Product model instance for the mockup image
        local_product_obj = Product.objects.filter(printify_id=product_id).first()
        mockup_image_url = local_product_obj.mockup_image.url if local_product_obj and local_product_obj.mockup_image else None

        product_data_for_template = {
            'id':str(item.get('id')),
            'title':item.get('title','N/A'),
            'description':item.get('description',''),
            'images':item.get('images',[]),
            'options':opts,
            'variants':proc_vars,
            'price': float(base_price) if isinstance(base_price, Decimal) else base_price,
            'mockup_image_url': mockup_image_url # Add mockup_image_url
        }
    except Exception as e:
        error_msg = f"Error fetching product {product_id}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        messages.error(request, f"Could not fetch product {product_id}.")
    return render(request, 'mystore/product_detail.html', {'product': product_data_for_template, 'error': error_msg})

@require_POST # Ensure only POST requests for add to cart
@login_required # Ensure user is logged in to add to cart
def add_to_cart(request, product_id=None): # product_id can be None if custom_design_id is passed
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Custom design path: Check for custom_design_id in POST data
    custom_design_id = request.POST.get('custom_design_id')

    cart = get_cart(request)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity <= 0:
            if is_ajax:
                return JsonResponse({'status':'error','message':'Quantity must be positive.'}, status=400)
            messages.error(request, "Quantity must be positive.");
            return redirect(request.META.get('HTTP_REFERER', reverse('product_list')))
    except ValueError:
        quantity = 1 # Default to 1 if invalid quantity provided

    item_added_or_updated = False
    final_message_text = "Error processing cart."

    if custom_design_id:
        # --- Handling Custom Design addition to cart ---
        try:
            custom_design = CustomDesign.objects.get(id=custom_design_id, user=request.user)
            if custom_design.status not in ['uploaded_to_printify', 'pending', 'added_to_cart']: # Allow re-adding
                return JsonResponse({'status': 'error', 'message': 'Custom design is not in a valid state to be added to cart.'}, status=400)
            
            cart_item_key = f"custom_design_{custom_design.id}" # Unique key for custom designs
            
            # Custom designs are unique instances, but we allow incrementing quantity for the same saved design
            if cart_item_key in cart:
                cart[cart_item_key]['quantity'] += quantity
                final_message_text = f"Added {quantity} more of your custom '{custom_design.product.title}' design to cart."
            else:
                price = custom_design.product.base_price_ngn # Use the base product price for now
                cart[cart_item_key] = {
                    'id': custom_design.product.printify_id, # Printify ID of the base product
                    'custom_design_id': str(custom_design.id),
                    'title': custom_design.product.title,
                    'variant_title': f"Custom: {custom_design.selected_size}, {custom_design.selected_color}", # Describe the custom variant
                    'price': float(price),
                    'quantity': quantity,
                    'image_url': custom_design.design_image.url, # Use the uploaded custom image URL
                    'is_custom': True,
                }
                final_message_text = f"Your custom '{custom_design.product.title}' design has been added to cart."
            
            custom_design.status = 'added_to_cart'
            custom_design.save()
            item_added_or_updated = True

        except CustomDesign.DoesNotExist:
            final_message_text = "Custom design not found or you do not have permission."
            logger.error(f"CustomDesign {custom_design_id} not found for user {request.user.id}.")
            item_added_or_updated = False
        except Exception as e:
            final_message_text = f"Error adding custom item: {str(e)}"
            logger.exception(f"Error adding custom design {custom_design_id} to cart:")
            item_added_or_updated = False

    else:
        # --- Original logic for adding standard Printify products to cart ---
        # This path is for non-customized products
        if not product_id: # This means no product_id was passed to the view, likely an error for standard products
            final_message_text = "Product ID is missing for standard product cart addition."
            item_added_or_updated = False
        else:
            product_id_str = str(product_id)
            selected_variant_id = request.POST.get('selected_variant_id')
            is_update = request.POST.get('update', 'false').lower() == 'true'
            
            cart_item_key = product_id_str # Default key if no variant is needed/selected
            if selected_variant_id and not is_update:
                cart_item_key = f"{product_id_str}-{selected_variant_id}"
            elif is_update:
                # When updating, the key should match the existing key in the cart
                # This needs to be carefully handled if product_id_str != product_id_str-variant_id
                # For updates, we usually get the full `cart_key` from the frontend
                cart_item_key = request.POST.get('cart_key', product_id_str) # Expect cart_key from frontend for updates

            if quantity <= 0 and is_update:
                if cart_item_key in cart:
                    # If it's a custom design being removed via update=true with quantity 0
                    if cart[cart_item_key].get('is_custom') and 'custom_design_id' in cart[cart_item_key]:
                        try:
                            custom_design_obj = CustomDesign.objects.get(id=cart[cart_item_key]['custom_design_id'])
                            custom_design_obj.delete() # This will also delete the associated image file
                            logger.info(f"🗑️ Deleted CustomDesign {custom_design_obj.id} when updating to 0 quantity.")
                        except CustomDesign.DoesNotExist:
                            logger.warning(f"⚠️ CustomDesign {cart[cart_item_key]['custom_design_id']} not found for deletion during update.")
                    
                    del cart[cart_item_key]
                    msg_text = "Item removed."
                else:
                    msg_text = "Item not found to remove."
                save_cart(request, cart)
                if is_ajax: return JsonResponse({'status':'success','message':msg_text,'cart_total_items':len(cart)})
                messages.success(request, msg_text); return redirect('view_cart')

            if cart_item_key in cart:
                title_msg = cart[cart_item_key].get('variant_title', cart[cart_item_key].get('title','Item'))
                if is_update:
                    cart[cart_item_key]['quantity'] = quantity
                    final_message_text = f"Updated {title_msg}."
                else:
                    cart[cart_item_key]['quantity'] += quantity
                    final_message_text = f"Added another {title_msg}."
                item_added_or_updated = True
            else:
                if not selected_variant_id:
                    final_message_text = "Please select a variant."
                elif not PRINTIFY_SHOP_ID or not PRINTIFY_API_TOKEN:
                    final_message_text = "Shop/API not configured."
                else:
                    url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id_str}.json"
                    try:
                        res = requests.get(url, headers=HEADERS, timeout=10)
                        res.raise_for_status()
                        item_data = res.json()
                        variant = next((v for v in item_data.get('variants',[]) if str(v.get('id'))==selected_variant_id),None)
                        if not variant:
                            final_message_text = "Variant not found."
                            raise ValueError(final_message_text)
                        
                        title = item_data.get('title','N/A')
                        v_title = variant.get('title','N/A')
                        price_ngn_decimal = (Decimal(variant.get('price',0))/Decimal('100.0'))*USD_TO_NGN_RATE
                        price_ngn = float(price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP))
                        img = item_data.get('images',[{}])[0].get('src','https://placehold.co/100x100?text=No+Img')
                        
                        cart[cart_item_key] = {
                            'id': product_id_str,
                            'variant_id': selected_variant_id,
                            'title': title,
                            'variant_title': v_title,
                            'price': price_ngn,
                            'quantity': quantity,
                            'image_url': img,
                            'is_custom': False,
                        }
                        final_message_text = f"Added {title} ({v_title}) to cart."
                        item_added_or_updated = True
                    except Exception as e:
                        final_message_text = f"Error adding item: {str(e)}"
                        logger.error(f"Error fetching Printify product {product_id_str} for cart: {e}")
    
    if item_added_or_updated:
        save_cart(request,cart)
        if is_ajax: return JsonResponse({'status':'success','message':final_message_text,'cart_total_items':len(cart)})
        messages.success(request,final_message_text)
    else:
        if is_ajax: return JsonResponse({'status':'error','message':final_message_text,'cart_total_items':len(cart)})
        messages.error(request,final_message_text)

    if is_update and not is_ajax: return redirect('view_cart')
    referer = request.META.get('HTTP_REFERER')
    if referer and request.get_host() in referer and not is_ajax: return redirect(referer)
    elif not is_ajax: return redirect('product_list')
    
    # Fallback for unexpected AJAX or non-AJAX redirects
    if is_ajax:
        # Ensure a valid JsonResponse is always returned for AJAX
        return JsonResponse({'status':'error','message':final_message_text or 'Unexpected AJAX issue.','cart_total_items':len(cart)}, status=500)
    return redirect('product_list')


def view_cart(request):
    cart = get_cart(request)
    cart_items_processed = {}
    cart_total_price = Decimal('0.0')

    for k, item_details in cart.items():
        try:
            price = Decimal(str(item_details.get('price',0.0)))
            quantity = int(item_details.get('quantity',0))
        except (ValueError, TypeError):
            price = Decimal('0.0')
            quantity = 0

        current_item = item_details.copy()
        current_item['price_per_unit_decimal'] = price
        current_item['price'] = float(price)
        current_item['quantity']=quantity
        current_item['total_price']= float(price*quantity)
        current_item['cart_key']=k
        cart_items_processed[k]=current_item
        cart_total_price+= (price*quantity)
    
    return render(request, 'mystore/cart.html', {'cart_items':cart_items_processed,'cart_total_price':cart_total_price})

@login_required
def remove_from_cart(request, cart_key):
    cart = get_cart(request)
    if cart_key in cart: 
        title = cart[cart_key].get('variant_title',cart[cart_key].get('title','Item'))
        # If it's a custom design, also delete the CustomDesign object from the database
        if cart[cart_key].get('is_custom') and 'custom_design_id' in cart[cart_key]:
            try:
                custom_design_obj = CustomDesign.objects.get(id=cart[cart_key]['custom_design_id'])
                custom_design_obj.delete() # This will also delete the associated image file
                logger.info(f"🗑️ Deleted CustomDesign {custom_design_obj.id} when removing from cart.")
            except CustomDesign.DoesNotExist:
                logger.warning(f"⚠️ CustomDesign {cart[cart_key]['custom_design_id']} not found for deletion.")
            
        del cart[cart_key]
        save_cart(request,cart)
        messages.success(request,f"Removed {title} from cart.")
    else: messages.error(request,"Item not found in cart. Could not remove.")
    return redirect('view_cart')

@login_required
def checkout_page(request):
    cart = get_cart(request)
    if not cart: messages.info(request, "Your cart is empty."); return redirect('view_cart')
    cart_items_display = {}; cart_total_price_decimal = Decimal('0.0')
    for cart_key, item_details in cart.items():
        try: price = Decimal(str(item_details.get('price', '0.0'))); quantity = int(item_details.get('quantity', 0))
        except (ValueError, TypeError): price = Decimal('0.0'); quantity = 0
        current_item = item_details.copy(); current_item['price_per_unit'] = float(price); current_item['quantity'] = quantity
        current_item['total_price'] = float(price * quantity); current_item['cart_key'] = cart_key
        cart_items_display[cart_key] = current_item; cart_total_price_decimal += (price * quantity)
    context = {'cart_items': cart_items_display, 'cart_total_price': cart_total_price_decimal, 'paystack_public_key': PAYSTACK_PUBLIC_KEY }
    return render(request, 'mystore/checkout.html', context)

@login_required
def checkout_submit(request):
    if request.method == 'POST':
        cart = get_cart(request)
        if not cart: messages.error(request, "Your cart is empty."); return redirect('view_cart')
        
        email = request.POST.get('email') or request.user.email
        name = request.POST.get('name', ''); first_name = name.split(' ')[0] if name else request.user.first_name or 'Customer'
        last_name = ' '.join(name.split(' ')[1:]) if ' ' in name else request.user.last_name or ''
        phone = request.POST.get('phone', ''); address = request.POST.get('address', ''); city = request.POST.get('city', ''); state_province = request.POST.get('state', '')
        zipcode = request.POST.get('zipcode', ''); country = request.POST.get('country', 'NG') # Default to NG for Nigeria
        
        cart_total_price_ngn_decimal = Decimal('0.0')
        cart_snapshot_for_session = {} # Store a copy of the cart for order creation
        
        printify_line_items = [] # Items to send to Printify

        for item_key, item_details in cart.items():
            item_price_decimal = Decimal(str(item_details.get('price', '0.0')))
            item_quantity = int(item_details.get('quantity', 0))
            cart_total_price_ngn_decimal += item_price_decimal * item_quantity
            
            cart_snapshot_for_session[item_key] = item_details.copy()
            cart_snapshot_for_session[item_key]['price'] = float(item_price_decimal)

            # Build Printify line item for each product in cart
            if item_details.get('is_custom'):
                try:
                    custom_design_obj = CustomDesign.objects.get(id=item_details['custom_design_id'], user=request.user)
                    if not custom_design_obj.printify_image_id:
                        raise ValueError(f"Custom design {custom_design_obj.id} has no Printify image ID. Please upload it first.")

                    # --- CRITICAL LOGIC FOR FINDING PRINTIFY VARIANT ID ---
                    # You need to map selected_size, selected_color to a Printify variant ID
                    matched_printify_variant_id = None
                    if custom_design_obj.product and custom_design_obj.product.variants_data:
                        # Iterate through the stored variants data to find a match
                        for pv in custom_design_obj.product.variants_data:
                            # This logic assumes variant title is "Color / Size" (e.g., "White / S")
                            # Or you need to check pv.get('option_value_ids') against what Printify expects
                            # E.g., if Printify sends option_value_ids as ['color_id_1', 'size_id_1']
                            # You would need to know the IDs for 'White' and 'S' from Printify.
                            # For simplicity, let's try matching the title if available.
                            if pv.get('title') == f"{custom_design_obj.selected_color} / {custom_design_obj.selected_size}" and pv.get('is_enabled') and pv.get('is_available'):
                                matched_printify_variant_id = pv.get('id')
                                break
                            # Alternative: More robust if Printify option values are consistent
                            # You'd need to fetch or map Printify's option_value_ids for the selected color/size.
                            # For example, if you know 'White' has option_value_id 'A' and 'S' has 'B':
                            # if 'A' in pv.get('option_value_ids', []) and 'B' in pv.get('option_value_ids', []):
                            #     matched_printify_variant_id = pv.get('id')
                            #     break

                    if not matched_printify_variant_id:
                        logger.error(f"Could not find matching Printify variant for custom design {custom_design_obj.id}: Product={custom_design_obj.product.title}, Size={custom_design_obj.selected_size}, Color={custom_design_obj.selected_color}")
                        raise ValueError(f"Could not find matching Printify variant for custom design {custom_design_obj.id}.")
                    
                    printify_line_items.append({
                        "product_id": custom_design_obj.product.printify_id, # Base Printify Product ID
                        "variant_id": matched_printify_variant_id, # The specific variant (size, color)
                        "quantity": item_quantity,
                        "print_provider_id": custom_design_obj.product.printify_print_provider_id, # Must be set on Product model
                        "images": [
                            {
                                "src": custom_design_obj.design_image.url, # Direct URL to your hosted image
                                "id": custom_design_obj.printify_image_id, # Printify's asset ID
                                # Adjust x, y, scale, angle, placement based on your design needs and Printify print area
                                # These are relative to the print area. 0.5, 0.5 centers it.
                                "x": 0.5,
                                "y": 0.5,
                                "scale": 1.0,
                                "angle": 0,
                                "placement": "front"
                            }
                        ]
                    })
                except CustomDesign.DoesNotExist:
                    logger.error(f"❌ Error: Custom design {item_details.get('custom_design_id')} not found during checkout.")
                    messages.error(request, "A custom item in your cart could not be processed. Please try again or remove it.")
                    return redirect('view_cart')
                except ValueError as ve:
                    logger.error(f"❌ Error with custom design Printify data: {ve}")
                    messages.error(request, f"Error with custom product configuration: {ve}. Please contact support.")
                    return redirect('view_cart')
                except Exception as e:
                    logger.exception(f"❌ Unexpected error processing custom design for Printify order: {e}")
                    messages.error(request, "An unexpected error occurred with your custom product. Please contact support.")
                    return redirect('view_cart')
            else:
                # For standard products, use their printify_id and selected_variant_id
                product_id_from_cart = item_details.get('id') # This is Printify product ID from original sync
                variant_id_from_cart = item_details.get('variant_id') # This is Printify variant ID from original sync
                
                # Retrieve the actual Product object from your DB to get print_provider_id
                local_product = Product.objects.filter(printify_id=product_id_from_cart).first()
                if not local_product:
                    logger.error(f"Product {product_id_from_cart} not found in database for order. Skipping.")
                    messages.error(request, f"Product {product_id_from_cart} not found in database for order. Please remove it from cart.")
                    return redirect('view_cart')
                
                printify_line_items.append({
                    "product_id": local_product.printify_id,
                    "variant_id": variant_id_from_cart,
                    "quantity": item_quantity,
                    "print_provider_id": local_product.printify_print_provider_id 
                })

        # Final checks before proceeding
        if not printify_line_items:
            messages.error(request, "No valid items found in cart for Printify order.")
            return redirect('view_cart')

        cart_total_price_kobo = int(cart_total_price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP) * 100)
        if cart_total_price_kobo <= 0:
            messages.error(request, "Order total is invalid.");
            return redirect('view_cart')

        # Create Printify Order Payload
        printify_order_payload = {
            "external_id": f"hoxobil_order_{uuid.uuid4().hex[:10]}", # A unique ID for Printify
            "order_items": printify_line_items,
            "shipping_method": 1, # Standard shipping. You might allow selection later.
            "is_approved": False, # Set to True to automatically send to production
            "address1": address,
            "city": city,
            "country": country, # Ensure this is a valid 2-letter ISO code (e.g., "NG")
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "state": state_province,
            "zip": zipcode,
        }
        
        # --- Paystack Initialization ---
        order_reference = f"HOXOBIL-{uuid.uuid4().hex[:10].upper()}"
        if not PAYSTACK_SECRET_KEY: messages.error(request, "Payment gateway not configured."); return redirect('checkout')
        
        init_url = f"{PAYSTACK_API_BASE_URL}/transaction/initialize"
        callback_url = request.build_absolute_uri(reverse('paystack_callback'))
        
        payload = {
            "email": email,
            "amount": cart_total_price_kobo,
            "currency": "NGN",
            "reference": order_reference,
            "callback_url": callback_url,
            "metadata": {
                "customer_name": name,
                "cart_id": request.session.session_key or "unknown_session",
                "order_items_count": len(cart),
                "user_id": request.user.id if request.user.is_authenticated else None
            }
        }
        paystack_headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        try:
            logger.info(f"🚀 Initializing Paystack. Ref: {order_reference}, Amount: {cart_total_price_kobo} Kobo")
            response = requests.post(init_url, headers=paystack_headers, json=payload, timeout=20)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"✅ Paystack Init Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("status"):
                authorization_url = response_data["data"]["authorization_url"]
                request.session['paystack_reference'] = order_reference
                # Store the Printify order payload in session for later use after Paystack success
                request.session['printify_order_payload'] = printify_order_payload 
                request.session['order_details_for_completion'] = {
                    'first_name': first_name, 'last_name': last_name, 'email': email, 'phone': phone,
                    'address': address, 'city': city, 'state': state_province, 'zipcode': zipcode,
                    'country': country,
                    'total_amount': float(cart_total_price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                    'cart_snapshot': cart_snapshot_for_session, # Store cart content to create OrderItems
                    'user_id': request.user.id if request.user.is_authenticated else None
                }
                logger.info(f"Redirecting to Paystack: {authorization_url}")
                return redirect(authorization_url)
            else:
                error_msg = response_data.get("message", "Failed to initialize payment.");
                messages.error(request, error_msg);
                logger.error(f"❌ Paystack Init Error: {error_msg}")
        except requests.exceptions.HTTPError as http_err:
            error_text = http_err.response.text if http_err.response is not None else "No response body"
            logger.error(f"❌ HTTPError Paystack init: {http_err} - Response: {error_text}")
            messages.error(request, "Could not connect to payment gateway.")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"❌ RequestException Paystack init: {req_err}")
            messages.error(request, "A network error occurred.")
        except Exception as e:
            logger.exception(f"❌ Unexpected error Paystack init:") # Uses logger.exception to get traceback
            messages.error(request, "An unexpected error occurred.")
        return redirect('checkout')
    return redirect('checkout')

@login_required
def paystack_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref')
    logger.info(f"📞 Paystack Callback received. Reference: {reference}")

    if not reference:
        messages.error(request, "Payment reference not found.");
        logger.error("❌ Callback: No reference found.");
        return redirect('checkout')

    session_reference = request.session.get('paystack_reference')
    if session_reference and session_reference != reference:
        logger.warning(f"⚠️ Callback: Reference mismatch or direct access. Session: '{session_reference}', Paystack: '{reference}'. Proceeding with Paystack's reference for verification.")
    
    # We explicitly remove the session reference now to prevent double processing attempts if user refreshes
    if 'paystack_reference' in request.session:
        del request.session['paystack_reference']
        request.session.modified = True

    if not PAYSTACK_SECRET_KEY:
        messages.error(request, "Payment gateway verification not configured.");
        logger.error("❌ Callback: Paystack secret key missing.");
        return redirect('checkout')

    verify_url = f"{PAYSTACK_API_BASE_URL}/transaction/verify/{reference}"
    paystack_headers = { "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}" }

    try:
        logger.info(f"🔎 Verifying Paystack transaction. URL: {verify_url}");
        response = requests.get(verify_url, headers=paystack_headers, timeout=15);
        response.raise_for_status()
        response_data = response.json();
        logger.info(f"✅ Paystack Verify Response: {json.dumps(response_data, indent=2)}")

        if response_data.get("status") and response_data["data"]["status"] == "success":
            logger.info("🎉 Payment Successful!");
            
            order_details_session = request.session.get('order_details_for_completion')
            printify_order_payload = request.session.get('printify_order_payload')

            if not order_details_session or not printify_order_payload:
                messages.error(request, "Order details lost. Contact support with reference: " + reference);
                logger.error(f"❌ Callback: 'order_details_for_completion' or 'printify_order_payload' missing from session for ref {reference}.");
                return redirect(reverse('order_failure_specific', kwargs={'error_message': "Order details lost after payment."}))

            cart_snapshot = order_details_session.pop('cart_snapshot', {})

            user_for_order = None
            user_id_from_session = order_details_session.pop('user_id', None)

            # Determine the user for the order
            if user_id_from_session:
                User = get_user_model()
                try:
                    user_for_order = User.objects.get(id=user_id_from_session)
                except User.DoesNotExist:
                    logger.warning(f"⚠️ User with ID {user_id_from_session} not found for order {reference}. Trying current request user.")
                    if request.user.is_authenticated:
                        user_for_order = request.user
                        logger.info(f"Using current request.user: {user_for_order.email} as user_for_order (session user ID {user_id_from_session} not found).")
            elif request.user.is_authenticated:
                user_for_order = request.user
                logger.info(f"No user_id in session, using current request.user: {user_for_order.email} as user_for_order.")

            # Prevent duplicate orders
            if Order.objects.filter(paystack_reference=reference).exists():
                messages.info(request, "This payment has already been processed.");
                logger.info(f"ℹ️ Order with reference {reference} already exists. Redirecting to success page.")
                # Clear session data to avoid issues even if it's a re-process
                if 'cart' in request.session: del request.session['cart']
                if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
                if 'printify_order_payload' in request.session: del request.session['printify_order_payload']
                request.session.modified = True
                return redirect('order_success', order_reference=reference)

            try:
                # Create the local Order in your database
                order_data = {
                    'first_name':order_details_session.get('first_name'), 'last_name':order_details_session.get('last_name'),
                    'email':order_details_session.get('email'), 'phone':order_details_session.get('phone'),
                    'address':order_details_session.get('address'), 'city':order_details_session.get('city'),
                    'state':order_details_session.get('state'), 'zipcode':order_details_session.get('zipcode'),
                    'country':order_details_session.get('country'),
                    'total_amount':Decimal(str(order_details_session.get('total_amount', '0.0'))).quantize(Decimal('0.01'), ROUND_HALF_UP),
                    'paid':True, 'paystack_reference':reference
                }
                if user_for_order:
                    order_data['user'] = user_for_order

                order = Order.objects.create(**order_data)
                logger.info(f"📝 Order {order.id} created locally for reference {reference}.")

                # Process OrderItems
                for item_key, item_data in cart_snapshot.items():
                    custom_design_id = item_data.get('custom_design_id')
                    custom_design_obj = None
                    product_obj = None # This will be the local Product model instance

                    if custom_design_id:
                        try:
                            custom_design_obj = CustomDesign.objects.get(id=custom_design_id, user=user_for_order) # Link to user who ordered
                            product_obj = custom_design_obj.product # Get the base product
                            # Update status for custom design to indicate it's part of an order
                            custom_design_obj.status = 'order_created'
                            custom_design_obj.save()
                        except CustomDesign.DoesNotExist:
                            logger.warning(f"⚠️ CustomDesign {custom_design_id} not found during order item creation for order {order.id}.")
                            # Consider how to handle: should this fail the entire order or proceed?
                            # For now, it will create OrderItem with custom_design=None.
                    else:
                        # For standard product, find the Product object
                        product_obj = Product.objects.filter(printify_id=item_data.get('id')).first()
                        if not product_obj:
                            logger.warning(f"⚠️ Product with Printify ID {item_data.get('id')} not found for order item {order.id}.")

                    OrderItem.objects.create(
                        order=order,
                        product=product_obj, # Link to your local Product model
                        custom_design=custom_design_obj, # Link to CustomDesign if applicable
                        product_title=item_data.get('title'),
                        variant_title=item_data.get('variant_title'),
                        quantity=item_data.get('quantity'),
                        price_at_purchase=Decimal(str(item_data.get('price', '0.0'))).quantize(Decimal('0.01'), ROUND_HALF_UP),
                        printify_variant_id=item_data.get('variant_id') # Store Printify variant ID if applicable
                    )
                logger.info(f"🛍️ Order items created for Order {order.id}.")

                # --- Create Order on Printify ---
                if PRINTIFY_API_TOKEN and PRINTIFY_SHOP_ID:
                    logger.info(f"📦 Attempting to create Printify order for shop {PRINTIFY_SHOP_ID} with payload: {json.dumps(printify_order_payload, indent=2)}")
                    try:
                        printify_response = printify_client.create_order(shop_id=PRINTIFY_SHOP_ID, order_payload=printify_order_payload)
                        if printify_response and printify_response.get('id'):
                            logger.info(f"✅ Printify Order created: {printify_response['id']}")
                            # Update your local Order model with Printify Order ID if you add a field for it
                            # order.printify_order_id = printify_response['id']
                            # order.save()
                            messages.success(request, "Payment successful and Printify order placed!")
                        else:
                            logger.error(f"❌ Failed to create Printify order. Response: {printify_response}")
                            messages.warning(request, "Payment successful, but failed to create Printify order. We'll handle this manually. Reference: " + reference)
                    except Exception as printify_e:
                        logger.exception(f"❌ Exception while creating Printify order for ref {reference}:")
                        messages.warning(request, "Payment successful, but an error occurred sending order to Printify. We'll handle this manually. Reference: " + reference)
                else:
                    logger.warning("⚠️ Printify API not configured. Order will not be sent to Printify automatically.")
                    messages.warning(request, "Payment successful, but Printify API not configured. Order will be processed manually. Reference: " + reference)

                # Clear session data after successful order and Printify call
                if 'cart' in request.session: del request.session['cart']
                if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
                if 'printify_order_payload' in request.session: del request.session['printify_order_payload']
                request.session.modified = True
                logger.info("🗑️ Cart and session payment data cleared.")

                return redirect('order_success', order_reference=reference)
            except Exception as e:
                logger.exception(f"❌ Error creating order in DB for ref {reference}:")
                messages.error(request, "Payment successful, but issue creating order. Contact support with reference: " + reference);
                return redirect(reverse('order_failure_specific', kwargs={'error_message': "DB order creation failed."}))
        else:
            error_msg = response_data["data"].get("gateway_response", "Payment not successful.") if response_data.get("data") else response_data.get("message", "Payment verification failed.")
            messages.error(request, f"Payment Failed: {error_msg}");
            logger.error(f"❌ Payment Failed/Verification Error for ref {reference}: {error_msg}");
            return redirect(reverse('order_failure_specific', kwargs={'error_message': error_msg}))
    except requests.exceptions.HTTPError as http_err:
        error_text = http_err.response.text if http_err.response is not None else "No response body"
        logger.error(f"❌ HTTPError Paystack verify ref {reference}: {http_err} - Response: {error_text}");
        messages.error(request, "Could not verify payment. Contact support if debited.")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"❌ RequestException Paystack verify ref {reference}: {req_err}");
        messages.error(request, "Network error verifying payment. Contact support.")
    except Exception as e:
        logger.exception(f"❌ Unexpected error Paystack verify ref {reference}:")
        messages.error(request, "Unexpected error verifying payment. Contact support.")

    return redirect('checkout')

def order_success(request, order_reference):
    try:
        order = Order.objects.get(paystack_reference=order_reference, paid=True)
        # Clear residual session data just in case
        if 'paystack_reference' in request.session: del request.session['paystack_reference']
        if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
        if 'printify_order_payload' in request.session: del request.session['printify_order_payload']
        request.session.modified = True
    except Order.DoesNotExist:
        messages.error(request, "Order not found or payment not confirmed.");
        return redirect('home')
    return render(request, 'mystore/order_success.html', {'order': order})

def order_failure(request, error_message=None):
    context = {'error_message': error_message or "Your payment could not be processed."}
    return render(request, 'mystore/order_failure.html', context)

def competition_page(request):
    prizes_left = WinningCode.objects.filter(is_claimed=False).count()
    launch_event = SiteEvent.objects.filter(event_name='SITE_LAUNCH', is_active=True).order_by('-event_datetime').first()
    launch_datetime_iso = None
    launch_notes = None
    user_profile = None

    if launch_event:
        launch_datetime_iso = launch_event.event_datetime.isoformat()
        launch_notes = launch_event.notes

    if request.user.is_authenticated:
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)
            logger.info(f"UserProfile created on-the-fly for {request.user.email} in competition_page view.")
        except Exception as e:
            logger.error(f"Error accessing user.profile in competition_page: {e}")
            user_profile = None

    context = {
        'prizes_left': prizes_left,
        'launch_datetime_iso': launch_datetime_iso,
        'launch_notes': launch_notes,
        'user_profile': user_profile
    }
    return render(request, 'mystore/competition.html', context)

@login_required
@require_POST
def submit_competition_code(request):
    submitted_code = request.POST.get('code', '').strip()
    if not submitted_code or not submitted_code.isdigit() or len(submitted_code) != 6:
        return JsonResponse({'status': 'error', 'message': 'Invalid code format.'})
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    attempt = CompetitionAttempt.objects.create(
        user=request.user,
        ip_address=ip,
        submitted_code=submitted_code,
        session_key=session_key
    )
    
    unclaimed_prizes_count = WinningCode.objects.filter(is_claimed=False).count()
    if unclaimed_prizes_count == 0:
        return JsonResponse({'status': 'all_claimed', 'message': 'Sorry, all prizes have been claimed!'})
    
    try:
        winning_code_entry = WinningCode.objects.get(code=submitted_code)
        if winning_code_entry.is_claimed:
            attempt.winning_code_matched = winning_code_entry
            attempt.save()
            return JsonResponse({'status': 'claimed', 'message': f"Oops! Code '{submitted_code}' already claimed by {winning_code_entry.claimed_by_user.email if winning_code_entry.claimed_by_user else 'someone else'}.", 'prizes_left': unclaimed_prizes_count })
        else:
            winning_code_entry.is_claimed = True
            winning_code_entry.claimed_by_user = request.user
            winning_code_entry.claimed_at = timezone.now()
            winning_code_entry.save()
            
            attempt.is_winner = True
            attempt.winning_code_matched = winning_code_entry
            attempt.save()
            
            prizes_left_now = WinningCode.objects.filter(is_claimed=False).count()
            return JsonResponse({'status': 'success', 'message': f"🎉 Congrats, {request.user.email}! '{submitted_code}' is a winning code! You've won: {winning_code_entry.prize_description}", 'prize': winning_code_entry.prize_description, 'prizes_left': prizes_left_now })
    except WinningCode.DoesNotExist:
        attempt.is_winner = False
        attempt.save()
        return JsonResponse({'status': 'failure', 'message': f"Sorry, '{submitted_code}' is not a winning code. Keep trying!", 'prizes_left': unclaimed_prizes_count })
    except Exception as e:
        logger.exception(f"Error in submit_competition_code:")
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'})

def signup_view(request):
    if request.user.is_authenticated: return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            referral_code_input = form.cleaned_data.get('referral_code', '').strip()
            if referral_code_input:
                try:
                    referrer_profile = UserProfile.objects.get(referral_code__iexact=referral_code_input)
                    new_user_profile, created = UserProfile.objects.get_or_create(user=user)
                    if created: logger.info(f"UserProfile created on demand for {user.email} during signup referral processing.")
                    new_user_profile.referred_by = referrer_profile.user
                    new_user_profile.save(update_fields=['referred_by', 'updated_at'])
                    process_successful_referral(referrer_profile)
                    messages.success(request, f"Account created! You were referred by {referrer_profile.user.email}.")
                except UserProfile.DoesNotExist: messages.warning(request, "Invalid referral code, but account created.")
                except Exception as e: logger.error(f"Error processing referral: {e}"); messages.error(request, "Account created, error with referral.")
            login(request, user)
            if not messages.get_messages(request): messages.success(request, "Registration successful!")
            return redirect('home')
        else:
            # Form is not valid, errors will be in form.errors
            pass # The template will render form.errors
    else:
        form = CustomUserCreationForm()
    return render(request, 'mystore/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated: return redirect('home')
    next_url_param = request.GET.get('next')
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Welcome back, {user.first_name or user.email}!")
                next_redirect = request.POST.get('next') or request.GET.get('next') or reverse('home')
                return redirect(next_redirect)
            else: messages.error(request,"Invalid email or password.")
        else:
            messages.error(request,"Invalid email or password.") # Form errors will be handled by template as well
    else:
        form = EmailAuthenticationForm()
    return render(request, 'mystore/login.html', {'form': form, 'next': next_url_param or ''})

@login_required
def logout_view(request):
    logout(request); messages.info(request, "You have successfully logged out."); return redirect('home')

def privacy_policy_view(request): return render(request, 'mystore/privacy_policy.html')
def terms_of_service_view(request): return render(request, 'mystore/terms_of_service.html')

def sync_products_to_db(products_from_api):
    created_count = 0
    updated_count = 0
    if not products_from_api: return 0, 0
    
    for pd in products_from_api:
        pid = str(pd.get("id"))
        title = pd.get("title", "N/A")
        desc = pd.get("description", "")
        img_url = pd.get("images", [{}])[0].get("src", "")
        options_data = pd.get('options', [])
        vars_api = pd.get("variants", [])
        
        # Get base price from the first variant if available
        p_cents = vars_api[0].get("price", 0) if vars_api else 0

        proc_vars = []
        
        # Determine blueprint and print provider IDs from Printify product data
        blueprint_id = pd.get('blueprint_id')
        # Print provider ID is usually available at the product level or in variants
        print_provider_id = pd.get('print_provider_id') 
        if not print_provider_id and vars_api: # Fallback to first variant's print_provider_id
            print_provider_id = vars_api[0].get('print_provider_id')


        for v_api in vars_api:
            v_p_cents = v_api.get("price",0)
            proc_vars.append({
                "id":str(v_api.get("id")),
                "title":v_api.get("title"),
                "price_cents":v_p_cents,
                "price_ngn":float((Decimal(v_p_cents)/Decimal('100.0'))*USD_TO_NGN_RATE.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                "sku":v_api.get("sku"),
                "is_available":v_api.get("is_available",True),
                "is_enabled":v_api.get("is_enabled",True),
                'option_value_ids': [str(opt_id) for opt_id in v_api.get('options', [])]
            })
        
        p_ngn_decimal = (Decimal(p_cents)/Decimal('100.0'))*USD_TO_NGN_RATE
        p_ngn = float(p_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP))

        defaults = {
            'title': title,
            'description': desc,
            'base_price_ngn': Decimal(p_ngn),
            'primary_image_url': img_url,
            'variants_data': proc_vars, # Store all variants data
            'product_options_data': options_data, # Store all options data
            'printify_shop_id': PRINTIFY_SHOP_ID,
            'printify_blueprint_id': blueprint_id, # Set blueprint ID
            'printify_print_provider_id': print_provider_id, # Set print provider ID
            'is_published': pd.get('visible', True),
            'last_synced_at': timezone.now(),
            # 'mockup_image': None, # This should be manually set in Django admin for each product
        }
        
        try:
            obj, cr = Product.objects.update_or_create(printify_id=pid, defaults=defaults)
            if cr: created_count += 1
            else: updated_count += 1
        except Exception as e:
            logger.error(f"DB Error syncing product {pid}: {e}")
            
    return created_count, updated_count

def sync_products_view(request):
    if not PRINTIFY_API_TOKEN or not PRINTIFY_SHOP_ID:
        messages.error(request, "API token or Shop ID not configured for sync.")
        return JsonResponse({'status': 'error', 'message': 'API token or Shop ID not configured.'})
    
    all_products_from_api = []
    page = 1
    while True:
        api_url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products.json?page={page}&limit=100"
        logger.info(f"   Fetching page {page} from {api_url}")
        try:
            response = requests.get(api_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            current_page_products = data.get('data', [])
            if not current_page_products: break
            
            all_products_from_api.extend(current_page_products)
            
            if data.get('current_page') == data.get('last_page') or not data.get('next_page_url'): break
            page += 1
        except Exception as e:
            error_msg = f'Failed to fetch products for sync (page {page}): {str(e)}'
            logger.error(f"❌ {error_msg}")
            messages.error(request, error_msg)
            return JsonResponse({'status': 'error', 'message': error_msg})
            
    if not all_products_from_api:
        messages.info(request, "No products found in Printify shop to sync.")
        return JsonResponse({'status': 'info', 'message': 'No products found in Printify shop to sync.'})
    
    logger.info(f"   Total products fetched from Printify API: {len(all_products_from_api)}")
    created, updated = sync_products_to_db(all_products_from_api)
    msg = f"Synchronization complete. Products created: {created}, Products updated: {updated}."
    logger.info(f"✅ {msg}")
    messages.success(request, msg)
    return JsonResponse({'status': 'success', 'message': msg, 'created': created, 'updated': updated})


# --- New Views for Customization ---

@login_required # Ensure user is logged in to customize
def product_customizer_view(request, product_id):
    """
    Renders the product customizer page for a specific product.
    Fetches the local Product object.
    """
    # Fetch the local Product object from your DB, not Printify API
    product = get_object_or_404(Product, id=product_id)
    
    context = {
        'product': product,
        # CSRF token is automatically included by Django's context processor in a normal render.
        # But if you manually need it (e.g., for meta tag), `request.META.get('CSRF_COOKIE', '')` is one way,
        # or just use `{% csrf_token %}` in the template for forms. The `meta` tag is fine.
    }
    return render(request, 'mystore/product_customizer.html', context)

@require_POST
@login_required # Only logged-in users can submit custom designs
def submit_custom_design(request):
    """
    Receives custom design data (image, options) from the frontend,
    saves the image locally, uploads it to Printify, and creates a CustomDesign object.
    """
    # Ensure it's an AJAX request (X-Requested-With header)
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request type.'}, status=400)

    product_id = request.POST.get('product_id')
    design_image_data_url = request.POST.get('design_image') # Base64 string from canvas.toDataURL()
    selected_product_type = request.POST.get('product_type')
    selected_size = request.POST.get('size')
    selected_color = request.POST.get('color')
    # design_json_str = request.POST.get('design_json') # Uncomment if you're sending Fabric.js JSON

    if not all([product_id, design_image_data_url, selected_product_type, selected_size, selected_color]):
        logger.error("Missing required fields for custom design submission.")
        return JsonResponse({'status': 'error', 'message': 'Missing required design data.'}, status=400)

    try:
        product_instance = get_object_or_404(Product, id=product_id)
        user = request.user # User is guaranteed to be authenticated by @login_required

        # Convert data URL to Django ContentFile
        # Expected format: data:image/png;base64,iVBORw0KGgo...
        _format, imgstr = design_image_data_url.split(';base64,')
        ext = _format.split('/')[-1] # e.g., 'png'
        
        # Create a unique filename for the design image
        file_name = f'custom_design_{slugify(product_instance.title)}_{uuid.uuid4().hex[:8]}.{ext}'
        data = ContentFile(base64.b64decode(imgstr), name=file_name)

        # 1. Save the CustomDesign to your database locally first
        custom_design = CustomDesign(
            user=user,
            product=product_instance,
            design_image=data, # Assign ContentFile
            # design_json=json.loads(design_json_str) if design_json_str else None,
            selected_product_type=selected_product_type,
            selected_size=selected_size,
            selected_color=selected_color,
            status='pending' # Initial status
        )
        custom_design.save() # Saves the image file to storage
        logger.info(f"✅ CustomDesign {custom_design.id} saved locally to DB.")

        # 2. Upload the image to Printify
        if not PRINTIFY_API_TOKEN:
            logger.warning("⚠️ Printify API Token is not set. Skipping image upload to Printify.")
            # Still return success, but inform the frontend that Printify upload was skipped
            return JsonResponse({
                'status': 'success',
                'message': 'Design saved! Printify upload skipped (API not configured).',
                'custom_design_id': custom_design.id,
                'redirect_url': reverse('view_cart') # Fallback redirect if no JS add to cart
            })

        upload_response = printify_client.upload_image(
            file_name=file_name,
            contents_base64=imgstr # Pass just the base64 string without 'data:image/png;base64,' part
        )

        if upload_response and upload_response.get('id'):
            custom_design.printify_image_id = upload_response['id']
            custom_design.status = 'uploaded_to_printify'
            custom_design.save()
            logger.info(f"✅ Design image uploaded to Printify with ID: {custom_design.printify_image_id}")

            return JsonResponse({
                'status': 'success',
                'message': 'Your custom design has been saved and uploaded to Printify!',
                'custom_design_id': custom_design.id,
                'redirect_url': reverse('view_cart') # Frontend can use this or call add_to_cart_custom_design_ajax
            })
        else:
            # If Printify upload fails
            custom_design.status = 'failed'
            custom_design.save()
            error_message = upload_response.get('error', 'Unknown Printify upload error.') if upload_response else 'No response from Printify or empty response.'
            logger.error(f"❌ Failed to upload image to Printify for design {custom_design.id}: {error_message}")
            return JsonResponse({'status': 'error', 'message': f'Failed to upload design to Printify: {error_message}'}, status=500)

    except Product.DoesNotExist:
        logger.error(f"Product with ID {product_id} not found for custom design submission.")
        return JsonResponse({'status': 'error', 'message': 'Base product not found.'}, status=404)
    except Exception as e:
        logger.exception("❌ Error during custom design submission:") # Logs full traceback
        # Attempt to mark custom design as failed if it was created
        if 'custom_design' in locals() and custom_design.status == 'pending':
            custom_design.status = 'failed'
            custom_design.save()
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred during design submission: {str(e)}'}, status=500)

@require_POST
@login_required
def add_to_cart_custom_design_ajax(request):
    """
    AJAX endpoint to add a *previously saved* CustomDesign to the user's cart.
    This acts as the second step after `submit_custom_design`.
    """
    custom_design_id = request.POST.get('custom_design_id')
    quantity = int(request.POST.get('quantity', 1)) # Usually 1 for custom designs

    if not custom_design_id:
        return JsonResponse({'status': 'error', 'message': 'Missing custom design ID.'}, status=400)

    try:
        # Ensure the CustomDesign belongs to the current user
        custom_design_obj = CustomDesign.objects.get(id=custom_design_id, user=request.user)
        
        # Modify the request.POST object to match what add_to_cart expects for a custom item.
        # This allows reusing the main add_to_cart logic.
        request.POST._mutable = True # Make POST data mutable
        request.POST['custom_design_id'] = str(custom_design_obj.id) # Ensure it's a string
        request.POST['quantity'] = str(quantity)
        # Remove any product_id or selected_variant_id that might confuse the add_to_cart function
        if 'product_id' in request.POST: del request.POST['product_id']
        if 'selected_variant_id' in request.POST: del request.POST['selected_variant_id']
        request.POST._mutable = False # Make POST data immutable again

        # Call the main add_to_cart view. It will now handle saving to session and updating status.
        # It will return a JsonResponse directly because this is an AJAX call.
        # We pass product_id=None because add_to_cart will use custom_design_id instead.
        return add_to_cart(request, product_id=None)

    except CustomDesign.DoesNotExist:
        logger.error(f"Custom design {custom_design_id} not found or does not belong to user {request.user.id}.")
        return JsonResponse({'status': 'error', 'message': 'Custom design not found or you do not have permission.'}, status=404)
    except Exception as e:
        logger.exception(f"Error adding custom design {custom_design_id} from ajax to cart:")
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)









        def test_page_view(request):
            
            """
A simple test view to check if the Django application is serving pages.
    """
    return HttpResponse("<h1>Hello from HOXOBIL! This is a test page.</h1><p>If you see this, your Django app is running!</p>")