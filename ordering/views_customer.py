import json
import uuid
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Restaurant, DiningTable, MenuCategory, FoodItem, FoodAddon, Order, OrderItem, OrderItemAddon

@ensure_csrf_cookie
def restaurant_menu_view(request, slug):
    """
    Public customer menu page for a specific restaurant.
    Accepts optional ?table=<table_number> query parameter.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    table_param = request.GET.get('table', '').strip()
    
    table_obj = None
    table_valid = False
    if table_param:
        table_obj = DiningTable.objects.filter(restaurant=restaurant, table_number__iexact=table_param, is_active=True).first()
        if table_obj:
            table_valid = True

    search_query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('cat', '').strip()
    veg_only = request.GET.get('veg', '') == '1'

    categories = MenuCategory.objects.filter(restaurant=restaurant, is_active=True).prefetch_related(
        'food_items'
    ).order_by('display_order', 'name')

    items_qs = FoodItem.objects.filter(restaurant=restaurant).select_related('category').prefetch_related('addons').order_by('category__display_order', 'display_order', 'name')

    if search_query:
        items_qs = items_qs.filter(name__icontains=search_query) | items_qs.filter(description__icontains=search_query)

    if category_slug:
        items_qs = items_qs.filter(category__slug=category_slug)

    if veg_only:
        items_qs = items_qs.filter(is_vegetarian=True)

    # Group items by category for structured layout
    categorized_items = {}
    for cat in categories:
        cat_items = [item for item in items_qs if item.category_id == cat.id]
        if cat_items:
            categorized_items[cat] = cat_items

    # Also list of all tables for dropdown fallback if customer wants to select table manually
    available_tables = DiningTable.objects.filter(restaurant=restaurant, is_active=True).order_by('table_number')

    context = {
        'restaurant': restaurant,
        'table_param': table_param,
        'table_obj': table_obj,
        'table_valid': table_valid,
        'categories': categories,
        'categorized_items': categorized_items,
        'all_items_count': items_qs.count(),
        'search_query': search_query,
        'active_cat_slug': category_slug,
        'veg_only': veg_only,
        'available_tables': available_tables,
    }
    return render(request, 'ordering/customer_menu.html', context)


@require_GET
def food_item_detail_api(request, slug, item_id):
    """
    Returns item data, addons, and options in JSON for the customization modal.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    item = get_object_or_404(FoodItem, pk=item_id, restaurant=restaurant)

    addons = [{
        'id': a.id,
        'name': a.name,
        'price': str(a.price),
    } for a in item.addons.filter(is_available=True)]

    data = {
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': str(item.price),
        'image': item.image.url if item.image else '',
        'is_vegetarian': item.is_vegetarian,
        'spice_level': item.spice_level,
        'is_available': item.is_available,
        'addons': addons,
        'currency': restaurant.currency_symbol,
    }
    return JsonResponse({'success': True, 'item': data})


@require_POST
def checkout_submit_api(request, slug):
    """
    Secure checkout submission with complete server-side price recalculation and verification.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    customer_name = str(data.get('customer_name', '')).strip()
    customer_phone = str(data.get('customer_phone', '')).strip()
    order_type = str(data.get('order_type', 'dine_in')).strip()
    table_number = str(data.get('table_number', '')).strip()
    delivery_address = str(data.get('delivery_address', '')).strip()
    special_notes = str(data.get('special_notes', '')).strip()
    cart_items = data.get('items', [])

    # Validation
    if not customer_name:
        return JsonResponse({'success': False, 'error': 'Please provide your name.'}, status=400)

    if not customer_phone:
        return JsonResponse({'success': False, 'error': 'Please provide a contact phone number.'}, status=400)

    if not cart_items or not isinstance(cart_items, list):
        return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)

    # Check order type capabilities
    if order_type == 'dine_in' and not restaurant.dine_in_enabled:
        return JsonResponse({'success': False, 'error': 'Dine-in ordering is currently disabled for this restaurant.'}, status=400)
    elif order_type == 'takeaway' and not restaurant.takeaway_enabled:
        return JsonResponse({'success': False, 'error': 'Takeaway is currently disabled for this restaurant.'}, status=400)
    elif order_type == 'delivery' and not restaurant.delivery_enabled:
        return JsonResponse({'success': False, 'error': 'Delivery is currently disabled for this restaurant.'}, status=400)

    dining_table = None
    if order_type == 'dine_in':
        if not table_number:
            return JsonResponse({'success': False, 'error': 'Please select or enter your table number for dine-in.'}, status=400)
        dining_table = DiningTable.objects.filter(restaurant=restaurant, table_number__iexact=table_number, is_active=True).first()

    if order_type == 'delivery' and not delivery_address:
        return JsonResponse({'success': False, 'error': 'Please provide your delivery address.'}, status=400)

    # Server-side price calculation
    server_subtotal = Decimal('0.00')
    prepared_items = []

    # Pre-fetch foods
    food_ids = [item.get('foodId') for item in cart_items if item.get('foodId')]
    food_map = {f.id: f for f in FoodItem.objects.filter(id__in=food_ids, restaurant=restaurant)}

    for raw_item in cart_items:
        fid = raw_item.get('foodId')
        food = food_map.get(fid)
        if not food:
            return JsonResponse({'success': False, 'error': f"An item in your cart is no longer available."}, status=400)

        if not food.is_available:
            return JsonResponse({'success': False, 'error': f'"{food.name}" is currently sold out / unavailable.'}, status=400)

        try:
            qty = int(raw_item.get('quantity', 1))
            if qty <= 0:
                continue
        except (ValueError, TypeError):
            continue

        item_unit_price = Decimal(str(food.price))
        selected_addons_data = raw_item.get('addons', [])
        valid_addons = []

        if selected_addons_data:
            addon_ids = [a.get('id') for a in selected_addons_data if a.get('id')]
            addons_qs = FoodAddon.objects.filter(id__in=addon_ids, food_item=food, is_available=True)
            for addon in addons_qs:
                item_unit_price += Decimal(str(addon.price))
                valid_addons.append({
                    'name': addon.name,
                    'price': Decimal(str(addon.price)),
                })

        item_subtotal = item_unit_price * qty
        server_subtotal += item_subtotal

        prepared_items.append({
            'food_obj': food,
            'name': food.name,
            'unit_price': item_unit_price,
            'quantity': qty,
            'spice_level': str(raw_item.get('spiceLevel', '')),
            'special_instructions': str(raw_item.get('specialInstructions', '')),
            'subtotal': item_subtotal,
            'addons': valid_addons,
        })

    if not prepared_items:
        return JsonResponse({'success': False, 'error': 'No valid items found in order.'}, status=400)

    if restaurant.minimum_order_amount > Decimal('0.00') and server_subtotal < restaurant.minimum_order_amount:
        return JsonResponse({
            'success': False,
            'error': f"Minimum order amount is {restaurant.currency_symbol}{restaurant.minimum_order_amount} (Current: {restaurant.currency_symbol}{server_subtotal})."
        }, status=400)

    # Tax & delivery calculation
    tax_rate = restaurant.tax_percentage / Decimal('100.0')
    tax_amount = (server_subtotal * tax_rate).quantize(Decimal('0.01'))
    delivery_fee = restaurant.delivery_fee if order_type == 'delivery' else Decimal('0.00')
    grand_total = (server_subtotal + tax_amount + delivery_fee).quantize(Decimal('0.01'))

    # Payment method mapping
    payment_method_map = {
        'dine_in': 'cash_at_counter',
        'takeaway': 'pay_at_pickup',
        'delivery': 'cash_on_delivery',
    }
    payment_method = payment_method_map.get(order_type, 'cash_at_counter')

    # Atomic order creation
    with transaction.atomic():
        now = timezone.now()
        date_str = now.strftime('%Y%m%d')
        random_suffix = uuid.uuid4().hex[:6].upper()
        order_number = f"ORD-{date_str}-{random_suffix}"

        order = Order.objects.create(
            restaurant=restaurant,
            order_number=order_number,
            order_type=order_type,
            dining_table=dining_table,
            table_identifier=table_number if order_type == 'dine_in' else '',
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address if order_type == 'delivery' else '',
            special_notes=special_notes,
            subtotal=server_subtotal,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            total_amount=grand_total,
            payment_method=payment_method,
            payment_status='unpaid',
            status='pending',
        )

        for p_item in prepared_items:
            order_item = OrderItem.objects.create(
                order=order,
                food_item=p_item['food_obj'],
                item_name=p_item['name'],
                unit_price=p_item['unit_price'],
                quantity=p_item['quantity'],
                spice_level=p_item['spice_level'],
                special_instructions=p_item['special_instructions'],
                subtotal=p_item['subtotal'],
            )
            for addon_dict in p_item['addons']:
                OrderItemAddon.objects.create(
                    order_item=order_item,
                    addon_name=addon_dict['name'],
                    price=addon_dict['price'],
                )

    redirect_url = f"/r/{restaurant.slug}/order/{order.access_token}/"
    return JsonResponse({
        'success': True,
        'order_number': order.order_number,
        'access_token': str(order.access_token),
        'redirect_url': redirect_url,
    })


def order_status_view(request, slug, access_token):
    """
    Secure order tracking page for customer.
    Uses UUID access_token so only the customer with the link can view it.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    order = get_object_or_404(
        Order.objects.prefetch_related('items__selected_addons'),
        restaurant=restaurant,
        access_token=access_token
    )

    statuses_sequence = ['pending', 'accepted', 'preparing', 'ready', 'completed']
    current_status = order.status

    try:
        current_step_idx = statuses_sequence.index(current_status)
    except ValueError:
        current_step_idx = -1 # Cancelled or other

    context = {
        'restaurant': restaurant,
        'order': order,
        'statuses_sequence': statuses_sequence,
        'current_step_idx': current_step_idx,
    }
    return render(request, 'ordering/order_status.html', context)


@require_GET
def order_status_api(request, slug, access_token):
    """
    Lightweight JSON endpoint for the customer page to poll for status updates.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    order = get_object_or_404(Order, restaurant=restaurant, access_token=access_token)

    return JsonResponse({
        'success': True,
        'status': order.status,
        'status_display': order.get_status_display(),
        'payment_status': order.payment_status,
        'payment_status_display': order.get_payment_status_display(),
        'updated_at': order.updated_at.strftime('%I:%M %p'),
    })

