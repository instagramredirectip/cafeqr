import json
from decimal import Decimal
from datetime import datetime, time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.conf import settings
from .models import Restaurant, RestaurantStaff, DiningTable, MenuCategory, FoodItem, FoodAddon, Order, OrderItem
from .decorators import restaurant_staff_required


def owner_login_view(request):
    """
    Dedicated restaurant owner and staff login view.
    """
    if request.user.is_authenticated:
        try:
            staff = RestaurantStaff.objects.get(user=request.user, is_active=True)
            return redirect('owner_dashboard')
        except RestaurantStaff.DoesNotExist:
            pass

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                staff = RestaurantStaff.objects.select_related('restaurant').get(user=user, is_active=True)
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username} ({staff.restaurant.name})!")
                return redirect('owner_dashboard')
            except RestaurantStaff.DoesNotExist:
                messages.error(request, "This account is not configured with an active restaurant profile.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'ordering/owner/login.html')


def owner_logout_view(request):
    """Logs out the user and redirects to login."""
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('owner_login')


@restaurant_staff_required
def owner_dashboard(request):
    """
    Main restaurant owner overview dashboard.
    Displays live key performance metrics, order states, and recent orders.
    """
    restaurant = request.restaurant
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    today_end = timezone.make_aware(datetime.combine(today, time.max))

    today_orders_qs = Order.objects.filter(restaurant=restaurant, created_at__range=(today_start, today_end))

    today_orders_count = today_orders_qs.count()
    today_sales = today_orders_qs.exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    active_statuses = ['pending', 'accepted', 'preparing', 'ready']
    active_orders_count = Order.objects.filter(restaurant=restaurant, status__in=active_statuses).count()
    pending_orders_count = Order.objects.filter(restaurant=restaurant, status='pending').count()

    food_items_count = FoodItem.objects.filter(restaurant=restaurant).count()
    available_items_count = FoodItem.objects.filter(restaurant=restaurant, is_available=True).count()
    unavailable_items_count = food_items_count - available_items_count

    recent_orders = Order.objects.filter(restaurant=restaurant).prefetch_related('items').order_by('-created_at')[:10]

    context = {
        'restaurant': restaurant,
        'today_orders_count': today_orders_count,
        'today_sales': today_sales,
        'active_orders_count': active_orders_count,
        'pending_orders_count': pending_orders_count,
        'food_items_count': food_items_count,
        'available_items_count': available_items_count,
        'unavailable_items_count': unavailable_items_count,
        'recent_orders': recent_orders,
    }
    return render(request, 'ordering/owner/dashboard.html', context)


@restaurant_staff_required
@require_GET
def owner_live_orders_api(request):
    """
    Polling API for dashboard: returns new orders and current active order counts.
    """
    restaurant = request.restaurant
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, time.min))

    active_statuses = ['pending', 'accepted', 'preparing', 'ready']
    active_qs = Order.objects.filter(restaurant=restaurant, status__in=active_statuses).order_by('-created_at')[:15]
    
    pending_count = Order.objects.filter(restaurant=restaurant, status='pending').count()
    today_count = Order.objects.filter(restaurant=restaurant, created_at__gte=today_start).count()
    today_sales = Order.objects.filter(restaurant=restaurant, created_at__gte=today_start).exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    orders_data = []
    for order in active_qs:
        orders_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'order_type': order.get_order_type_display(),
            'table': order.table_identifier or (order.dining_table.table_number if order.dining_table else '-'),
            'total': f"{restaurant.currency_symbol}{order.total_amount}",
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': timezone.localtime(order.created_at).strftime('%I:%M %p'),
            'item_count': order.item_count,
        })

    return JsonResponse({
        'success': True,
        'pending_count': pending_count,
        'active_count': active_qs.count(),
        'today_count': today_count,
        'today_sales': f"{restaurant.currency_symbol}{today_sales:.2f}",
        'orders': orders_data,
    })


@restaurant_staff_required
def owner_orders_list(request):
    """
    Searchable and filterable full order management screen.
    """
    restaurant = request.restaurant
    orders_qs = Order.objects.filter(restaurant=restaurant).prefetch_related('items__selected_addons').order_by('-created_at')

    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all' and status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    order_type_filter = request.GET.get('type', 'all')
    if order_type_filter != 'all' and order_type_filter:
        orders_qs = orders_qs.filter(order_type=order_type_filter)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(table_identifier__icontains=search_query)
        )

    date_filter = request.GET.get('date', 'all')
    today = timezone.localdate()
    if date_filter == 'today':
        orders_qs = orders_qs.filter(created_at__date=today)
    elif date_filter == 'yesterday':
        yesterday = today - timezone.timedelta(days=1)
        orders_qs = orders_qs.filter(created_at__date=yesterday)

    paginator = Paginator(orders_qs, 20)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    context = {
        'restaurant': restaurant,
        'orders': orders_page,
        'status_filter': status_filter,
        'order_type_filter': order_type_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'total_orders_count': orders_qs.count(),
    }
    return render(request, 'ordering/owner/orders_list.html', context)


@restaurant_staff_required
def owner_order_detail(request, order_id):
    """
    Detailed inspection of a specific order with actions to advance status.
    """
    restaurant = request.restaurant
    order = get_object_or_404(Order.objects.prefetch_related('items__selected_addons'), id=order_id, restaurant=restaurant)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_payment = request.POST.get('payment_status')

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
        if new_payment in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = new_payment

        order.save()
        messages.success(request, f"Order {order.order_number} updated successfully.")
        return redirect('owner_order_detail', order_id=order.id)

    context = {
        'restaurant': restaurant,
        'order': order,
    }
    return render(request, 'ordering/owner/order_detail.html', context)


@restaurant_staff_required
@require_POST
def owner_order_update_status_api(request, order_id):
    """
    AJAX endpoint for changing order status directly from lists/dashboards.
    """
    restaurant = request.restaurant
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

    try:
        data = json.loads(request.body.decode('utf-8'))
        new_status = data.get('status')
    except Exception:
        new_status = request.POST.get('status')

    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        return JsonResponse({
            'success': True,
            'new_status': order.status,
            'new_status_display': order.get_status_display(),
            'message': f"Order status updated to {order.get_status_display()}."
        })

    return JsonResponse({'success': False, 'error': 'Invalid status specified.'}, status=400)


@restaurant_staff_required
def owner_menu_list(request):
    """
    Menu item management: list, filter, and quick toggle item availability.
    """
    restaurant = request.restaurant
    categories = MenuCategory.objects.filter(restaurant=restaurant).order_by('display_order', 'name')
    items_qs = FoodItem.objects.filter(restaurant=restaurant).select_related('category').prefetch_related('addons').order_by('category__display_order', 'display_order', 'name')

    cat_filter = request.GET.get('category')
    if cat_filter:
        items_qs = items_qs.filter(category_id=cat_filter)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        items_qs = items_qs.filter(name__icontains=search_query)

    context = {
        'restaurant': restaurant,
        'categories': categories,
        'items': items_qs,
        'selected_cat': cat_filter,
        'search_query': search_query,
    }
    return render(request, 'ordering/owner/menu_list.html', context)


@restaurant_staff_required
def owner_food_add(request):
    """
    Add a new food item with optional add-on configurations.
    """
    restaurant = request.restaurant
    categories = MenuCategory.objects.filter(restaurant=restaurant, is_active=True).order_by('display_order')

    if not categories.exists():
        messages.warning(request, "Please create at least one category before adding food items.")
        return redirect('owner_categories')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '0.00').strip()
        spice_level = request.POST.get('spice_level', 'Medium')
        is_veg = request.POST.get('is_vegetarian') == 'on'
        is_avail = request.POST.get('is_available') == 'on'
        display_order = request.POST.get('display_order', 0)
        image_file = request.FILES.get('image')

        category = get_object_or_404(MenuCategory, id=category_id, restaurant=restaurant)

        try:
            food = FoodItem.objects.create(
                restaurant=restaurant,
                category=category,
                name=name,
                description=description,
                price=Decimal(price),
                spice_level=spice_level,
                is_vegetarian=is_veg,
                is_available=is_avail,
                display_order=int(display_order or 0),
                image=image_file,
            )

            # Process add-ons
            addon_names = request.POST.getlist('addon_names[]')
            addon_prices = request.POST.getlist('addon_prices[]')
            for a_name, a_price in zip(addon_names, addon_prices):
                a_name = a_name.strip()
                if a_name:
                    try:
                        p = Decimal(a_price.strip() or '0.00')
                    except Exception:
                        p = Decimal('0.00')
                    FoodAddon.objects.create(food_item=food, name=a_name, price=p)

            messages.success(request, f'Food item "{food.name}" created successfully!')
            return redirect('owner_menu_list')
        except Exception as e:
            messages.error(request, f"Error saving food item: {e}")

    context = {
        'restaurant': restaurant,
        'categories': categories,
        'spice_choices': FoodItem.SPICE_CHOICES,
    }
    return render(request, 'ordering/owner/food_form.html', context)


@restaurant_staff_required
def owner_food_edit(request, item_id):
    """
    Edit existing food item and its add-on options.
    """
    restaurant = request.restaurant
    food = get_object_or_404(FoodItem.objects.prefetch_related('addons'), id=item_id, restaurant=restaurant)
    categories = MenuCategory.objects.filter(restaurant=restaurant, is_active=True).order_by('display_order')

    if request.method == 'POST':
        food.name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        food.category = get_object_or_404(MenuCategory, id=category_id, restaurant=restaurant)
        food.description = request.POST.get('description', '').strip()
        food.price = Decimal(request.POST.get('price', '0.00').strip())
        food.spice_level = request.POST.get('spice_level', 'Medium')
        food.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        food.is_available = request.POST.get('is_available') == 'on'
        food.display_order = int(request.POST.get('display_order', 0) or 0)

        if 'image' in request.FILES:
            food.image = request.FILES['image']

        food.save()

        # Sync add-ons
        food.addons.all().delete()
        addon_names = request.POST.getlist('addon_names[]')
        addon_prices = request.POST.getlist('addon_prices[]')
        for a_name, a_price in zip(addon_names, addon_prices):
            a_name = a_name.strip()
            if a_name:
                try:
                    p = Decimal(a_price.strip() or '0.00')
                except Exception:
                    p = Decimal('0.00')
                FoodAddon.objects.create(food_item=food, name=a_name, price=p)

        messages.success(request, f'Updated "{food.name}" successfully!')
        return redirect('owner_menu_list')

    context = {
        'restaurant': restaurant,
        'food': food,
        'categories': categories,
        'spice_choices': FoodItem.SPICE_CHOICES,
    }
    return render(request, 'ordering/owner/food_form.html', context)


@restaurant_staff_required
@require_POST
def owner_food_toggle_availability(request, item_id):
    """
    Quick toggle for item in/out of stock.
    """
    restaurant = request.restaurant
    food = get_object_or_404(FoodItem, id=item_id, restaurant=restaurant)
    food.is_available = not food.is_available
    food.save(update_fields=['is_available'])

    return JsonResponse({
        'success': True,
        'is_available': food.is_available,
        'message': f'"{food.name}" is now {"Available" if food.is_available else "Marked Unavailable / Sold Out"}.'
    })


@restaurant_staff_required
@require_POST
def owner_food_delete(request, item_id):
    """
    Safe food item deletion.
    """
    restaurant = request.restaurant
    food = get_object_or_404(FoodItem, id=item_id, restaurant=restaurant)
    name = food.name
    food.delete()
    messages.success(request, f'Food item "{name}" was deleted.')
    return redirect('owner_menu_list')


@restaurant_staff_required
def owner_categories(request):
    """
    Category management: view, add, and reorder.
    """
    restaurant = request.restaurant
    categories = MenuCategory.objects.filter(restaurant=restaurant).annotate(item_count=Count('food_items')).order_by('display_order', 'name')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        display_order = int(request.POST.get('display_order', 0) or 0)
        is_active = request.POST.get('is_active') == 'on'

        if name:
            MenuCategory.objects.create(
                restaurant=restaurant,
                name=name,
                description=description,
                display_order=display_order,
                is_active=is_active,
            )
            messages.success(request, f'Category "{name}" created successfully!')
            return redirect('owner_categories')

    context = {
        'restaurant': restaurant,
        'categories': categories,
    }
    return render(request, 'ordering/owner/categories.html', context)


@restaurant_staff_required
@require_POST
def owner_category_delete(request, category_id):
    """
    Delete category if no items are attached or after confirmation.
    """
    restaurant = request.restaurant
    cat = get_object_or_404(MenuCategory, id=category_id, restaurant=restaurant)
    name = cat.name
    cat.delete()
    messages.success(request, f'Category "{name}" was removed.')
    return redirect('owner_categories')


@restaurant_staff_required
def owner_qr_management(request):
    """
    QR Code central hub:
    - Live domain base URL status
    - General Restaurant Menu QR
    - Table-specific QR codes
    - Table creation
    - Print-friendly QR card generator
    """
    restaurant = request.restaurant
    site_base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')

    # Ensure general QR is created
    if not restaurant.general_qr_code:
        restaurant.generate_general_qr(site_base_url)
        restaurant.save(update_fields=['general_qr_code'])

    tables = DiningTable.objects.filter(restaurant=restaurant).order_by('table_number')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_table':
            table_no = request.POST.get('table_number', '').strip()
            capacity = int(request.POST.get('capacity', 4) or 4)
            if table_no:
                if DiningTable.objects.filter(restaurant=restaurant, table_number__iexact=table_no).exists():
                    messages.error(request, f"Table number '{table_no}' already exists.")
                else:
                    t = DiningTable.objects.create(restaurant=restaurant, table_number=table_no, capacity=capacity)
                    t.generate_qr(site_base_url)
                    t.save()
                    messages.success(request, f"Dining Table {table_no} created and QR code generated!")
                    return redirect('owner_qr_management')

        elif action == 'regenerate_all_qr':
            restaurant.generate_general_qr(site_base_url)
            restaurant.save(update_fields=['general_qr_code'])
            for t in tables:
                t.generate_qr(site_base_url)
                t.save(update_fields=['qr_code_image'])
            messages.success(request, f"All QR codes successfully regenerated using base domain: {site_base_url}")
            return redirect('owner_qr_management')

    context = {
        'restaurant': restaurant,
        'site_base_url': site_base_url,
        'tables': tables,
    }
    return render(request, 'ordering/owner/qr_management.html', context)


@restaurant_staff_required
@require_POST
def owner_table_delete(request, table_id):
    restaurant = request.restaurant
    table = get_object_or_404(DiningTable, id=table_id, restaurant=restaurant)
    no = table.table_number
    table.delete()
    messages.success(request, f"Table {no} was removed.")
    return redirect('owner_qr_management')


@restaurant_staff_required
def owner_table_print_view(request, table_id=None):
    """
    Print-friendly card for physical display on tables or restaurant counters.
    """
    restaurant = request.restaurant
    site_base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')

    table = None
    if table_id:
        table = get_object_or_404(DiningTable, id=table_id, restaurant=restaurant)
        if not table.qr_code_image:
            table.generate_qr(site_base_url)
            table.save(update_fields=['qr_code_image'])
        qr_image_url = table.qr_code_image.url
        target_url = table.get_table_url(site_base_url)
        card_title = f"Table {table.table_number}"
    else:
        if not restaurant.general_qr_code:
            restaurant.generate_general_qr(site_base_url)
            restaurant.save(update_fields=['general_qr_code'])
        qr_image_url = restaurant.general_qr_code.url
        target_url = restaurant.get_menu_url(site_base_url)
        card_title = "Dine-In & Takeaway Menu"

    context = {
        'restaurant': restaurant,
        'table': table,
        'qr_image_url': qr_image_url,
        'target_url': target_url,
        'card_title': card_title,
    }
    return render(request, 'ordering/owner/print_qr.html', context)


@restaurant_staff_required
def owner_settings(request):
    """
    Manage restaurant branding, contact info, order capabilities, and fees.
    """
    restaurant = request.restaurant

    if request.method == 'POST':
        restaurant.name = request.POST.get('name', '').strip()
        restaurant.tagline = request.POST.get('tagline', '').strip()
        restaurant.description = request.POST.get('description', '').strip()
        restaurant.phone = request.POST.get('phone', '').strip()
        restaurant.email = request.POST.get('email', '').strip()
        restaurant.address = request.POST.get('address', '').strip()
        restaurant.opening_hours = request.POST.get('opening_hours', '').strip()
        restaurant.currency_symbol = request.POST.get('currency_symbol', '$').strip()

        restaurant.dine_in_enabled = request.POST.get('dine_in_enabled') == 'on'
        restaurant.takeaway_enabled = request.POST.get('takeaway_enabled') == 'on'
        restaurant.delivery_enabled = request.POST.get('delivery_enabled') == 'on'

        try:
            restaurant.tax_percentage = Decimal(request.POST.get('tax_percentage', '5.00').strip() or '0.00')
            restaurant.delivery_fee = Decimal(request.POST.get('delivery_fee', '2.50').strip() or '0.00')
            restaurant.minimum_order_amount = Decimal(request.POST.get('minimum_order_amount', '0.00').strip() or '0.00')
        except Exception:
            pass

        if 'logo' in request.FILES:
            restaurant.logo = request.FILES['logo']
        if 'cover_image' in request.FILES:
            restaurant.cover_image = request.FILES['cover_image']

        restaurant.save()
        messages.success(request, "Restaurant settings updated successfully!")
        return redirect('owner_settings')

    context = {
        'restaurant': restaurant,
    }
    return render(request, 'ordering/owner/settings.html', context)

