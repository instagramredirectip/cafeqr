import uuid
import io
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.conf import settings
import qrcode
from PIL import Image

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    tagline = models.CharField(max_length=255, blank=True, help_text="Short, elegant restaurant tagline")
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField()
    
    logo = models.ImageField(upload_to='restaurant/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='restaurant/covers/', blank=True, null=True)
    
    opening_hours = models.CharField(max_length=200, default='11:00 AM - 11:00 PM')
    currency_symbol = models.CharField(max_length=10, default='$')
    
    # Order type capabilities
    dine_in_enabled = models.BooleanField(default=True, help_text="Allow customers to order for table dine-in")
    takeaway_enabled = models.BooleanField(default=True, help_text="Allow takeaway / pickup orders")
    delivery_enabled = models.BooleanField(default=True, help_text="Allow home delivery orders")
    
    # Financial settings
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'), help_text="Tax percentage (e.g. 5.00 for 5%)")
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('2.50'), help_text="Flat delivery fee")
    minimum_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # General Menu QR Code
    general_qr_code = models.ImageField(upload_to='restaurant/qrcodes/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_menu_url(self, base_url=None):
        base = (base_url or getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        return f"{base}/r/{self.slug}/menu/"

    def generate_general_qr(self, base_url=None):
        """Generates and saves the restaurant-wide menu QR code."""
        url = self.get_menu_url(base_url)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#32150F", back_color="#FDF3EC") # Brand styled QR!
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.slug}_general.png"
        self.general_qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)


class RestaurantStaff(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner / Administrator'),
        ('manager', 'Floor Manager'),
        ('staff', 'Kitchen / Order Staff'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='staff_members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Restaurant Staff'
        indexes = [
            models.Index(fields=['user', 'restaurant']),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.restaurant.name}"


class DiningTable(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=20, help_text="e.g. 1, 2, 5, Patio-A, VIP-1")
    capacity = models.PositiveIntegerField(default=4)
    qr_code_image = models.ImageField(upload_to='qrcodes/tables/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['table_number']
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'table_number'], name='unique_table_per_restaurant')
        ]
        indexes = [
            models.Index(fields=['restaurant', 'table_number']),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - Table {self.table_number}"

    def get_table_url(self, base_url=None):
        base = (base_url or getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        return f"{base}/r/{self.restaurant.slug}/menu/?table={self.table_number}"

    def generate_qr(self, base_url=None):
        """Generates and saves a table-specific QR code."""
        url = self.get_table_url(base_url)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#32150F", back_color="#FDF3EC") # Brand styled
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.restaurant.slug}_table_{self.table_number}.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)


class MenuCategory(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Menu Categories'
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'slug'], name='unique_category_slug_per_restaurant')
        ]
        indexes = [
            models.Index(fields=['restaurant', 'display_order']),
            models.Index(fields=['restaurant', 'is_active']),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while MenuCategory.objects.filter(restaurant=self.restaurant, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class FoodItem(models.Model):
    SPICE_CHOICES = [
        ('None', 'None'),
        ('Mild', 'Mild'),
        ('Medium', 'Medium'),
        ('Spicy', 'Spicy'),
        ('Extra Hot', 'Extra Hot'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='food_items')
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='food_items')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='food_items/', blank=True, null=True)
    
    is_vegetarian = models.BooleanField(default=False)
    spice_level = models.CharField(max_length=20, choices=SPICE_CHOICES, default='Medium')
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['restaurant', 'category', 'is_available']),
            models.Index(fields=['restaurant', 'display_order']),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.currency_symbol}{self.price})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while FoodItem.objects.filter(restaurant=self.restaurant, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class FoodAddon(models.Model):
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['price', 'name']

    def __str__(self):
        return f"{self.name} (+{self.food_item.restaurant.currency_symbol}{self.price})"


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash_at_counter', 'Pay at Restaurant / Counter'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('pay_at_pickup', 'Pay at Pickup'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
    dining_table = models.ForeignKey(DiningTable, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    table_identifier = models.CharField(max_length=50, blank=True, help_text="Historical snapshot of table number")
    
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=30)
    delivery_address = models.TextField(blank=True)
    special_notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='cash_at_counter')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['restaurant', '-created_at']),
            models.Index(fields=['access_token']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()}) - {self.restaurant.name}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='historical_orders')
    item_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    spice_level = models.CharField(max_length=20, blank=True)
    special_instructions = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"


class OrderItemAddon(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='selected_addons')
    addon_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.addon_name} (+{self.price})"
