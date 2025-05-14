from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse 
from .models import Product, Order, OrderItem, WinningCode, CompetitionAttempt, SiteEvent, UserProfile 
import requests 
import os
import json
import uuid 
from django.contrib import messages 
from django.conf import settings 
from decimal import Decimal, ROUND_HALF_UP 
from django.utils import timezone 
from django.views.decorators.http import require_POST 
from django.contrib.auth.forms import AuthenticationForm # UserCreationForm is replaced by CustomUserCreationForm
from django.contrib.auth import login, logout, authenticate, get_user_model 
from django.contrib.auth.decorators import login_required 
from collections import defaultdict
from django.contrib.auth.views import redirect_to_login
from .forms import CustomUserCreationForm, EmailAuthenticationForm # Import your custom forms
from .signals import process_successful_referral # Assuming this is where you defined it

# --- Configuration ---
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID', '18789476') 
PRINTIFY_API_TOKEN = os.getenv("PRINTIFY_API_TOKEN")
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY') 
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY') 

if not PRINTIFY_API_TOKEN: print("🔴 CRITICAL WARNING: PRINTIFY_API_TOKEN is not set.")
if not PAYSTACK_SECRET_KEY: print("🔴 CRITICAL WARNING: PAYSTACK_SECRET_KEY is not set.")

HEADERS = { 'Authorization': f'Bearer {PRINTIFY_API_TOKEN}', 'Content-Type': 'application/json'}
USD_TO_NGN_RATE = Decimal('1607.00') 
API_BASE_URL = "https://api.printify.com/v1"
PAYSTACK_API_BASE_URL = "https://api.paystack.co"

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
    api_url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products.json"; categorized_products = defaultdict(list); error_message_for_template = None 
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=15); response.raise_for_status()  
        raw_products = response.json().get('data', []) 
        for item in raw_products:
            variants = item.get('variants', []); price_cents = variants[0].get('price', 0) if variants else 0
            price_ngn = (Decimal(price_cents) / Decimal('100.0')) * USD_TO_NGN_RATE
            img_url = item.get('images', [{}])[0].get('src', 'https://placehold.co/600x400?text=No+Image')
            product_title = item.get('title', 'No Title'); category = infer_category_from_title(product_title)
            proc_variants = []
            for v_data in variants:
                v_price_cents = Decimal(v_data.get('price', 0))
                v_price_ngn = (v_price_cents / Decimal('100.0')) * USD_TO_NGN_RATE
                proc_variants.append({'id': str(v_data.get('id')), 'title': v_data.get('title', 'N/A'), 'price_ngn': float(v_price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'is_enabled': v_data.get('is_enabled', False), 'is_available': v_data.get('is_available', True), 'option_value_ids': [str(oid) for oid in v_data.get('options',[])] })
            product_item_data = {'id': str(item.get('id')), 'title': product_title, 'price': float(price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'image_url': img_url, 'variants': proc_variants, 'options': item.get('options', []) }
            categorized_products[category].append(product_item_data)
    except Exception as e: error_message_for_template = f"Error fetching products: {str(e)}"; print(f"❌ {error_message_for_template}"); messages.error(request, "Could not fetch products.")
    return render(request, 'mystore/products.html', {'categorized_products': dict(categorized_products), 'error': error_message_for_template })

def product_detail(request, product_id):
    if not PRINTIFY_API_TOKEN or not PRINTIFY_SHOP_ID: messages.error(request, "API/Shop token not configured."); return render(request, 'mystore/product_detail.html', {'product': None, 'error': 'Configuration error.'})
    url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id}.json"; product_data_for_template = None; error_msg = None
    try:
        res = requests.get(url, headers=HEADERS, timeout=10); res.raise_for_status(); item = res.json()
        opts = [{'name':o.get('name'),'type':o.get('type'),'values':[{'id':str(v.get('id')),'title':v.get('title')} for v in o.get('values',[])]} for o in item.get('options',[])]
        proc_vars = []
        for v_data in item.get('variants', []):
            v_price_ngn = (Decimal(v_data.get('price',0))/Decimal('100.0'))*USD_TO_NGN_RATE
            proc_vars.append({'id':str(v_data.get('id')),'title':v_data.get('title','N/A'), 'price_ngn':float(v_price_ngn.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'is_enabled':v_data.get('is_enabled',False),'is_available':v_data.get('is_available',True), 'option_value_ids':[str(oid) for oid in v_data.get('options',[])]})
        base_price = proc_vars[0]['price_ngn'] if proc_vars else 0.0
        product_data_for_template = {'id':str(item.get('id')),'title':item.get('title','N/A'),'description':item.get('description',''),'images':item.get('images',[]),'options':opts,'variants':proc_vars, 'price': float(base_price) if isinstance(base_price, Decimal) else base_price } 
    except Exception as e: error_msg = f"Error fetching product {product_id}: {str(e)}"; print(f"❌ {error_msg}"); messages.error(request, f"Could not fetch product {product_id}.")
    return render(request, 'mystore/product_detail.html', {'product': product_data_for_template, 'error': error_msg})

def add_to_cart(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not request.user.is_authenticated:
        if is_ajax:
            next_url = request.POST.get('current_page_url', request.get_full_path()) 
            login_url_with_next = f"{reverse('login')}?next={next_url}" 
            return JsonResponse({'status': 'login_required', 'message': 'Please sign in to add items to your cart.', 'login_url': login_url_with_next}, status=401)
        else: messages.info(request, "Please sign in to add items to your cart."); return redirect_to_login(request.get_full_path())
    product_id_str = str(product_id); selected_variant_id = request.POST.get('selected_variant_id'); cart = get_cart(request)
    try: quantity = int(request.POST.get('quantity',1))
    except ValueError: quantity = 1
    is_update = request.POST.get('update','false').lower()=='true'; cart_item_key = product_id_str
    if selected_variant_id and not is_update: cart_item_key = f"{product_id_str}-{selected_variant_id}"
    elif is_update: cart_item_key = product_id_str 
    if quantity <= 0 and is_update:
        if cart_item_key in cart: del cart[cart_item_key]; msg_text = "Item removed."
        else: msg_text = "Item not found to remove."
        save_cart(request,cart)
        if is_ajax: return JsonResponse({'status':'success','message':msg_text,'cart_total_items':len(cart)})
        messages.success(request, msg_text); return redirect('view_cart')
    elif quantity <= 0 and not is_update:
        msg_text = "Quantity must be positive."
        if is_ajax: return JsonResponse({'status':'error','message':msg_text,'cart_total_items':len(cart)})
        messages.error(request, msg_text); return redirect(request.META.get('HTTP_REFERER', reverse('product_list')))
    item_added_or_updated = False; final_message_text = "Error processing cart."
    if cart_item_key in cart:
        title_msg = cart[cart_item_key].get('variant_title', cart[cart_item_key].get('title','Item'))
        if is_update: cart[cart_item_key]['quantity'] = quantity; final_message_text = f"Updated {title_msg}."
        else: cart[cart_item_key]['quantity'] += quantity; final_message_text = f"Added another {title_msg}."
        item_added_or_updated = True
    else:
        if not selected_variant_id: final_message_text = "Please select a variant."
        elif not PRINTIFY_SHOP_ID or not PRINTIFY_API_TOKEN: final_message_text = "Shop/API not configured."
        else:
            url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id_str}.json" 
            try:
                res = requests.get(url, headers=HEADERS, timeout=10); res.raise_for_status(); item_data = res.json()
                variant = next((v for v in item_data.get('variants',[]) if str(v.get('id'))==selected_variant_id),None)
                if not variant: final_message_text = "Variant not found."; raise ValueError(final_message_text)
                title=item_data.get('title','N/A'); v_title=variant.get('title','N/A'); 
                price_ngn_decimal=(Decimal(variant.get('price',0))/Decimal('100.0'))*USD_TO_NGN_RATE; 
                price_ngn = float(price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP)) 
                img=item_data.get('images',[{}])[0].get('src','https://placehold.co/100x100?text=No+Img')
                cart[cart_item_key]={'id':product_id_str,'variant_id':selected_variant_id,'title':title,'variant_title':v_title,'price':price_ngn,'quantity':quantity,'image_url':img}
                final_message_text=f"Added {title} ({v_title}) to cart."; item_added_or_updated=True
            except Exception as e: final_message_text = f"Error adding item: {str(e)}"
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
    if is_ajax: return JsonResponse({'status':'error','message':'Unexpected AJAX issue.','cart_total_items':len(cart)}) 
    return redirect('product_list')

def view_cart(request):
    cart = get_cart(request); cart_items_processed = {}; cart_total_price = Decimal('0.0')
    for k, item_details in cart.items():
        price = Decimal(str(item_details.get('price',0.0))); quantity = int(item_details.get('quantity',0)) 
        current_item = item_details.copy(); 
        current_item['price_per_unit_decimal'] = price 
        current_item['price'] = float(price) 
        current_item['quantity']=quantity
        current_item['total_price']= float(price*quantity) 
        current_item['cart_key']=k
        cart_items_processed[k]=current_item; 
        cart_total_price+= (price*quantity) 
    return render(request, 'mystore/cart.html', {'cart_items':cart_items_processed,'cart_total_price':cart_total_price})

@login_required
def remove_from_cart(request, cart_key):
    cart = get_cart(request)
    if cart_key in cart: title = cart[cart_key].get('variant_title',cart[cart_key].get('title','Item')); del cart[cart_key]; save_cart(request,cart); messages.success(request,f"Removed {title} from cart.")
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
        zipcode = request.POST.get('zipcode', ''); country = request.POST.get('country', 'NG')
        cart_total_price_ngn_decimal = Decimal('0.0'); cart_snapshot_for_session = {} 
        for item_key, item_details in cart.items():
            item_price_decimal = Decimal(str(item_details.get('price', '0.0'))); item_quantity = int(item_details.get('quantity', 0))
            cart_total_price_ngn_decimal += item_price_decimal * item_quantity
            cart_snapshot_for_session[item_key] = item_details.copy(); cart_snapshot_for_session[item_key]['price'] = float(item_price_decimal) 
        cart_total_price_kobo = int(cart_total_price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP) * 100) 
        if cart_total_price_kobo <= 0: messages.error(request, "Order total is invalid."); return redirect('view_cart')
        order_reference = f"HOXOBIL-{uuid.uuid4().hex[:10].upper()}"
        if not PAYSTACK_SECRET_KEY: messages.error(request, "Payment gateway not configured."); return redirect('checkout')
        init_url = f"{PAYSTACK_API_BASE_URL}/transaction/initialize"; callback_url = request.build_absolute_uri(reverse('paystack_callback'))
        payload = {"email": email, "amount": cart_total_price_kobo, "currency": "NGN", "reference": order_reference, "callback_url": callback_url, "metadata": { "customer_name": name, "cart_id": request.session.session_key or "unknown_session", "order_items_count": len(cart), "user_id": request.user.id if request.user.is_authenticated else None }}
        paystack_headers = { "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json" }
        try:
            print(f"🚀 Initializing Paystack. Ref: {order_reference}, Amount: {cart_total_price_kobo} Kobo")
            response = requests.post(init_url, headers=paystack_headers, json=payload, timeout=20); response.raise_for_status() 
            response_data = response.json(); print(f"✅ Paystack Init Response: {json.dumps(response_data, indent=2)}")
            if response_data.get("status"):
                authorization_url = response_data["data"]["authorization_url"]
                request.session['paystack_reference'] = order_reference 
                request.session['order_details_for_completion'] = {'first_name': first_name, 'last_name': last_name, 'email': email, 'phone': phone, 'address': address, 'city': city, 'state': state_province, 'zipcode': zipcode, 'country': country, 'total_amount': float(cart_total_price_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP)), 'cart_snapshot': cart_snapshot_for_session, 'user_id': request.user.id if request.user.is_authenticated else None }
                print(f"Redirecting to Paystack: {authorization_url}"); return redirect(authorization_url)
            else: error_msg = response_data.get("message", "Failed to initialize payment."); messages.error(request, error_msg); print(f"❌ Paystack Init Error: {error_msg}")
        except requests.exceptions.HTTPError as http_err: error_text = http_err.response.text if http_err.response is not None else "No response body"; print(f"❌ HTTPError Paystack init: {http_err} - Response: {error_text}"); messages.error(request, "Could not connect to payment gateway.")
        except requests.exceptions.RequestException as req_err: print(f"❌ RequestException Paystack init: {req_err}"); messages.error(request, "A network error occurred.")
        except Exception as e: print(f"❌ Unexpected error Paystack init: {e}"); messages.error(request, "An unexpected error occurred.")
        return redirect('checkout')
    return redirect('checkout')

@login_required 
def paystack_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref'); 
    print(f"📞 Paystack Callback received. Reference: {reference}")

    if not reference: 
        messages.error(request, "Payment reference not found."); 
        print("❌ Callback: No reference found."); 
        return redirect('checkout') 
    
    session_reference = request.session.get('paystack_reference')
    if session_reference != reference:
         print(f"⚠️ Callback: Reference mismatch or direct access. Session: '{session_reference}', Paystack: '{reference}'. Proceeding with Paystack's reference for verification.")
    
    if not PAYSTACK_SECRET_KEY: 
        messages.error(request, "Payment gateway verification not configured."); 
        print("❌ Callback: Paystack secret key missing."); 
        return redirect('checkout')

    verify_url = f"{PAYSTACK_API_BASE_URL}/transaction/verify/{reference}"; 
    paystack_headers = { "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}" }

    try:
        print(f"🔎 Verifying Paystack transaction. URL: {verify_url}"); 
        response = requests.get(verify_url, headers=paystack_headers, timeout=15); 
        response.raise_for_status()
        response_data = response.json(); 
        print(f"✅ Paystack Verify Response: {json.dumps(response_data, indent=2)}")

        if response_data.get("status") and response_data["data"]["status"] == "success":
            print("🎉 Payment Successful!"); 
            order_details_session = request.session.get('order_details_for_completion')
            
            if not order_details_session: 
                messages.error(request, "Order details lost. Contact support with reference: " + reference); 
                print(f"❌ Callback: 'order_details_for_completion' missing from session for ref {reference}."); 
                return redirect(reverse('order_failure_specific', kwargs={'error_message': "Order details lost after payment."}))
            
            cart_snapshot = order_details_session.pop('cart_snapshot', {}) 
            
            user_for_order = None
            user_id_from_session = order_details_session.pop('user_id', None) 
            
            # *** CORRECTED INDENTATION AND LOGIC FOR USER ASSIGNMENT ***
            if user_id_from_session: 
                User = get_user_model() 
                try:
                    user_for_order = User.objects.get(id=user_id_from_session)
                except User.DoesNotExist:
                    print(f"⚠️ User with ID {user_id_from_session} not found for order {reference}. Order will be created without a user link.")
                    # Fallback to current request.user if session user_id is invalid but user is logged in now
                    if request.user.is_authenticated:
                        user_for_order = request.user
                        print(f"  Using current request.user: {user_for_order.email} as user_for_order (session user ID {user_id_from_session} not found).") # Use .email for CustomUser
            elif request.user.is_authenticated: # This elif corresponds to the outer "if user_id_from_session:"
                user_for_order = request.user
                print(f"  No user_id in session, using current request.user: {user_for_order.email} as user_for_order.") # Use .email
            # *** END CORRECTION ***
            

            if Order.objects.filter(paystack_reference=reference).exists():
                messages.info(request, "Payment already processed."); 
                print(f"ℹ️ Order with reference {reference} already exists.")
                if 'cart' in request.session: request.session['cart'] = {}
                if 'paystack_reference' in request.session: del request.session['paystack_reference']
                if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
                request.session.modified = True; 
                return redirect('order_success', order_reference=reference) 
            
            try:
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
                print(f"📝 Order {order.id} created.")
                for item_key, item_data in cart_snapshot.items(): OrderItem.objects.create(order=order, product_title=item_data.get('title'), variant_title=item_data.get('variant_title'), quantity=item_data.get('quantity'), price_at_purchase=Decimal(str(item_data.get('price', '0.0'))).quantize(Decimal('0.01'), ROUND_HALF_UP))
                print(f"🛍️ Order items created for Order {order.id}.")
                request.session['cart'] = {}; 
                if 'paystack_reference' in request.session: del request.session['paystack_reference']
                if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
                request.session.modified = True; print("🗑️ Cart and session payment data cleared.")
                messages.success(request, "Payment successful! Your order has been placed."); 
                return redirect('order_success', order_reference=reference) 
            except Exception as e: 
                print(f"❌ Error creating order in DB for ref {reference}: {e}"); 
                messages.error(request, "Payment successful, but issue creating order. Contact support with reference: " + reference); 
                return redirect(reverse('order_failure_specific', kwargs={'error_message': "DB order creation failed."})) 
        else: 
            error_msg = response_data["data"].get("gateway_response", "Payment not successful.") if response_data.get("data") else response_data.get("message", "Payment verification failed."); 
            messages.error(request, f"Payment Failed: {error_msg}"); 
            print(f"❌ Payment Failed/Verification Error for ref {reference}: {error_msg}"); 
            return redirect(reverse('order_failure_specific', kwargs={'error_message': error_msg})) 
    except requests.exceptions.HTTPError as http_err: 
        error_text = http_err.response.text if http_err.response is not None else "No response body"; 
        print(f"❌ HTTPError Paystack verify ref {reference}: {http_err} - Response: {error_text}"); 
        messages.error(request, "Could not verify payment. Contact support if debited.")
    except requests.exceptions.RequestException as req_err: 
        print(f"❌ RequestException Paystack verify ref {reference}: {req_err}"); 
        messages.error(request, "Network error verifying payment. Contact support.")
    except Exception as e: 
        print(f"❌ Unexpected error Paystack verify ref {reference}: {e}"); 
        messages.error(request, "Unexpected error verifying payment. Contact support.")
        
    return redirect('checkout') 

def order_success(request, order_reference):
    try:
        order = Order.objects.get(paystack_reference=order_reference, paid=True)
        if 'paystack_reference' in request.session: del request.session['paystack_reference']
        if 'order_details_for_completion' in request.session: del request.session['order_details_for_completion']
        request.session.modified = True
    except Order.DoesNotExist: messages.error(request, "Order not found or payment not confirmed."); return redirect('home') 
    return render(request, 'mystore/order_success.html', {'order': order})

def order_failure(request, error_message=None): 
    context = {'error_message': error_message or "Your payment could not be processed."}
    return render(request, 'mystore/order_failure.html', context)

def competition_page(request):
    prizes_left = WinningCode.objects.filter(is_claimed=False).count()
    launch_event = SiteEvent.objects.filter(event_name='SITE_LAUNCH', is_active=True).order_by('-event_datetime').first()
    launch_datetime_iso = None; launch_notes = None; user_profile = None
    if launch_event: 
        launch_datetime_iso = launch_event.event_datetime.isoformat()
        launch_notes = launch_event.notes 
    if request.user.is_authenticated:
        try: 
            user_profile = request.user.profile
        except UserProfile.DoesNotExist: 
            user_profile = UserProfile.objects.create(user=request.user)
            print(f"UserProfile created on-the-fly for {request.user.email} in competition_page view.")
        except Exception as e: 
            print(f"Error accessing user.profile in competition_page: {e}")
            user_profile = None
    context = { 'prizes_left': prizes_left, 'launch_datetime_iso': launch_datetime_iso, 'launch_notes': launch_notes, 'user_profile': user_profile }
    return render(request, 'mystore/competition.html', context)

@login_required 
@require_POST 
def submit_competition_code(request):
    submitted_code = request.POST.get('code', '').strip()
    if not submitted_code or not submitted_code.isdigit() or len(submitted_code) != 6: return JsonResponse({'status': 'error', 'message': 'Invalid code format.'})
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR'); ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    session_key = request.session.session_key; 
    if not session_key: request.session.save(); session_key = request.session.session_key
    attempt = CompetitionAttempt.objects.create(user=request.user, ip_address=ip, submitted_code=submitted_code, session_key=session_key)
    unclaimed_prizes_count = WinningCode.objects.filter(is_claimed=False).count()
    if unclaimed_prizes_count == 0: return JsonResponse({'status': 'all_claimed', 'message': 'Sorry, all prizes have been claimed!'})
    try:
        winning_code_entry = WinningCode.objects.get(code=submitted_code)
        if winning_code_entry.is_claimed:
            attempt.winning_code_matched = winning_code_entry; attempt.save()
            return JsonResponse({'status': 'claimed', 'message': f"Oops! Code '{submitted_code}' already claimed by {winning_code_entry.claimed_by_user.email if winning_code_entry.claimed_by_user else 'someone'}.", 'prizes_left': unclaimed_prizes_count })
        else:
            winning_code_entry.is_claimed = True; winning_code_entry.claimed_by_user = request.user; winning_code_entry.claimed_at = timezone.now(); winning_code_entry.save()
            attempt.is_winner = True; attempt.winning_code_matched = winning_code_entry; attempt.save()
            prizes_left_now = WinningCode.objects.filter(is_claimed=False).count()
            return JsonResponse({'status': 'success', 'message': f"🎉 Congrats, {request.user.email}! '{submitted_code}' is a winning code! You've won: {winning_code_entry.prize_description}", 'prize': winning_code_entry.prize_description, 'prizes_left': prizes_left_now })
    except WinningCode.DoesNotExist:
        attempt.is_winner = False; attempt.save()
        return JsonResponse({'status': 'failure', 'message': f"Sorry, '{submitted_code}' is not a winning code. Keep trying!", 'prizes_left': unclaimed_prizes_count })
    except Exception as e: print(f"Error in submit_competition_code: {e}"); return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'})

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
                    if created: print(f"UserProfile created on demand for {user.email} during signup referral processing.")
                    new_user_profile.referred_by = referrer_profile.user
                    new_user_profile.save(update_fields=['referred_by', 'updated_at'])
                    process_successful_referral(referrer_profile) # Call the function
                    messages.success(request, f"Account created! You were referred by {referrer_profile.user.email}.")
                except UserProfile.DoesNotExist: messages.warning(request, "Invalid referral code, but account created.")
                except Exception as e: print(f"Error processing referral: {e}"); messages.error(request, "Account created, error with referral.")
            login(request, user) 
            if not messages.get_messages(request): messages.success(request, "Registration successful!")
            return redirect('home') 
        else:
            # Errors are now handled by the template via {{ form.errors }} or {{ field.errors }}
            # You can still add a general message if you like, but it might be redundant.
            # messages.error(request, "Please correct the errors below.")
            pass
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
            messages.error(request,"Invalid email or password.") 
    else: 
        form = EmailAuthenticationForm()
    return render(request, 'mystore/login.html', {'form': form, 'next': next_url_param or ''})

@login_required 
def logout_view(request): 
    logout(request); messages.info(request, "You have successfully logged out."); return redirect('home')

def privacy_policy_view(request): return render(request, 'mystore/privacy_policy.html')
def terms_of_service_view(request): return render(request, 'mystore/terms_of_service.html')

def sync_products_to_db(products_from_api): # ... (your existing sync_products_to_db) ...
    created_count = 0; updated_count = 0
    if not products_from_api: return 0, 0
    for pd in products_from_api:
        pid = str(pd.get("id")); title = pd.get("title", "N/A"); desc = pd.get("description", "")
        img_url = pd.get("images", [{}])[0].get("src", "")
        options_data = pd.get('options', []) 
        vars_api = pd.get("variants", [])
        p_cents = vars_api[0].get("price", 0) if vars_api else 0
        proc_vars = []
        for v_api in vars_api:
            v_p_cents = v_api.get("price",0)
            proc_vars.append({"id":str(v_api.get("id")), "title":v_api.get("title"), "price_cents":v_p_cents, "price_ngn":float((Decimal(v_p_cents)/Decimal('100.0'))*USD_TO_NGN_RATE.quantize(Decimal('0.01'), ROUND_HALF_UP)), "sku":v_api.get("sku"), "is_available":v_api.get("is_available",True), "is_enabled":v_api.get("is_enabled",True), 'option_value_ids': [str(opt_id) for opt_id in v_api.get('options', [])]})
        p_ngn_decimal = (Decimal(p_cents)/Decimal('100.0'))*USD_TO_NGN_RATE
        p_ngn = float(p_ngn_decimal.quantize(Decimal('0.01'), ROUND_HALF_UP)) 
        
        defs = {'title':title,'description':desc,'base_price_ngn':Decimal(p_ngn),'primary_image_url':img_url, 
                'variants_data':proc_vars, 'product_options_data': options_data, 
                'printify_shop_id': PRINTIFY_SHOP_ID, 
                'is_published': pd.get('visible', True), 
                'last_synced_at': timezone.now()
               }
        try: 
            obj,cr = Product.objects.update_or_create(printify_id=pid,defaults=defs)
            if cr: created_count += 1
            else: updated_count += 1
        except Exception as e: print(f"DB Error syncing product {pid}: {e}")
    return created_count, updated_count
def sync_products_view(request): # ... (your existing sync_products_view) ...
    if not PRINTIFY_API_TOKEN or not PRINTIFY_SHOP_ID:
        messages.error(request, "API token or Shop ID not configured for sync.") 
        return JsonResponse({'status': 'error', 'message': 'API token or Shop ID not configured.'})
    all_products_from_api = []
    page = 1
    while True:
        api_url = f"{API_BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products.json?page={page}&limit=100" 
        print(f"  Fetching page {page} from {api_url}")
        try:
            response = requests.get(api_url, headers=HEADERS, timeout=20); response.raise_for_status()
            data = response.json(); current_page_products = data.get('data', [])
            if not current_page_products: break 
            all_products_from_api.extend(current_page_products)
            if data.get('current_page') == data.get('last_page') or not data.get('next_page_url'): break
            page += 1
        except Exception as e: error_msg = f'Failed to fetch products for sync (page {page}): {str(e)}'; print(f"❌ {error_msg}"); messages.error(request, error_msg); return JsonResponse({'status': 'error', 'message': error_msg})
    if not all_products_from_api: messages.info(request, "No products found in Printify shop to sync."); return JsonResponse({'status': 'info', 'message': 'No products found in Printify shop to sync.'})
    print(f"  Total products fetched from Printify API: {len(all_products_from_api)}")
    created, updated = sync_products_to_db(all_products_from_api) 
    msg = f"Synchronization complete. Products created: {created}, Products updated: {updated}."
    print(f"✅ {msg}"); messages.success(request, msg) 
    return JsonResponse({'status': 'success', 'message': msg, 'created': created, 'updated': updated})

