import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    Restaurant, RestaurantStaff, MenuCategory, FoodItem,
    FoodAddon, DiningTable, Order, OrderItem, OrderItemAddon
)

class MultiRestaurantOrderingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Restaurant A
        self.rest_a = Restaurant.objects.create(
            name='Spice Garden',
            slug='spice-garden',
            phone='1234567890',
            address='123 Spice Rd',
            currency_symbol='$',
            tax_percentage=Decimal('5.00'),
            delivery_fee=Decimal('3.00'),
            dine_in_enabled=True,
            takeaway_enabled=True,
            delivery_enabled=True,
        )
        self.rest_a.generate_general_qr()
        self.rest_a.save()

        # Owner A
        self.user_a = User.objects.create_user(username='owner_a', password='Password123!')
        self.staff_a = RestaurantStaff.objects.create(user=self.user_a, restaurant=self.rest_a, role='owner')

        # Create Restaurant B
        self.rest_b = Restaurant.objects.create(
            name='Pizza Bella',
            slug='pizza-bella',
            phone='9876543210',
            address='456 Crust Blvd',
            currency_symbol='$',
            tax_percentage=Decimal('8.00'),
            delivery_fee=Decimal('2.00'),
            dine_in_enabled=True,
            takeaway_enabled=True,
            delivery_enabled=True,
        )
        self.rest_b.generate_general_qr()
        self.rest_b.save()

        # Owner B
        self.user_b = User.objects.create_user(username='owner_b', password='Password123!')
        self.staff_b = RestaurantStaff.objects.create(user=self.user_b, restaurant=self.rest_b, role='owner')

        # Regular user without staff profile
        self.user_regular = User.objects.create_user(username='regular_customer', password='Password123!')

        # Categories & Items for Restaurant A
        self.cat_a = MenuCategory.objects.create(restaurant=self.rest_a, name='Mains', slug='mains', display_order=1)
        self.dish_a = FoodItem.objects.create(
            restaurant=self.rest_a,
            category=self.cat_a,
            name='Chicken Tikka Masala',
            slug='chicken-tikka-masala',
            description='Rich and creamy',
            price=Decimal('15.00'),
            is_available=True,
        )
        self.addon_a = FoodAddon.objects.create(food_item=self.dish_a, name='Garlic Naan', price=Decimal('3.00'))

        # Tables for Restaurant A
        self.table_a5 = DiningTable.objects.create(restaurant=self.rest_a, table_number='5', capacity=4)
        self.table_a5.generate_qr()
        self.table_a5.save()

        # Categories & Items for Restaurant B
        self.cat_b = MenuCategory.objects.create(restaurant=self.rest_b, name='Pizzas', slug='pizzas', display_order=1)
        self.dish_b = FoodItem.objects.create(
            restaurant=self.rest_b,
            category=self.cat_b,
            name='Margherita Pizza',
            slug='margherita-pizza',
            description='Fresh basil and cheese',
            price=Decimal('12.00'),
            is_available=True,
        )

    # 1. Access Control Tests
    def test_unauthenticated_user_redirected_from_dashboard(self):
        resp = self.client.get(reverse('owner_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/owner/login/', resp.url)

    def test_non_staff_user_cannot_access_dashboard(self):
        self.client.login(username='regular_customer', password='Password123!')
        resp = self.client.get(reverse('owner_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/owner/login/', resp.url)

    def test_owner_a_cannot_see_restaurant_b_orders(self):
        # Create an order in Restaurant B
        order_b = Order.objects.create(
            restaurant=self.rest_b,
            order_number='ORD-B-1001',
            order_type='dine_in',
            table_identifier='1',
            customer_name='Bob',
            customer_phone='555-0102',
            subtotal=Decimal('12.00'),
            total_amount=Decimal('12.96'),
        )

        self.client.login(username='owner_a', password='Password123!')
        resp = self.client.get(reverse('owner_orders_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'ORD-B-1001')
        self.assertNotContains(resp, 'Bob')

        # Directly accessing order B detail gives 404
        resp_detail = self.client.get(reverse('owner_order_detail', args=[order_b.id]))
        self.assertEqual(resp_detail.status_code, 404)

    def test_owner_a_cannot_edit_restaurant_b_food(self):
        self.client.login(username='owner_a', password='Password123!')
        resp = self.client.get(reverse('owner_food_edit', args=[self.dish_b.id]))
        self.assertEqual(resp.status_code, 404)

    # 2. Menu Management & Immediate Customer Reflectivity
    def test_owner_price_update_reflects_on_customer_menu(self):
        self.client.login(username='owner_a', password='Password123!')

        # Update dish price from 15.00 to 18.50
        post_data = {
            'name': 'Chicken Tikka Masala Premium',
            'category': self.cat_a.id,
            'description': 'Upgraded spices',
            'price': '18.50',
            'spice_level': 'Medium',
            'is_available': 'on',
            'display_order': 0,
        }
        resp = self.client.post(reverse('owner_food_edit', args=[self.dish_a.id]), post_data)
        self.assertEqual(resp.status_code, 302)

        # Check public customer menu
        resp_menu = self.client.get(reverse('restaurant_menu', args=[self.rest_a.slug]))
        self.assertEqual(resp_menu.status_code, 200)
        self.assertContains(resp_menu, '$18.50')
        self.assertContains(resp_menu, 'Chicken Tikka Masala Premium')

    # 3. Server-Side Price Verification and Order Creation
    def test_server_side_price_verification_ignores_client_tampering(self):
        # Attempt to submit order claiming unit price is $1.00 when DB price is $15.00 + $3.00 addon = $18.00
        payload = {
            'customer_name': 'Alice Smith',
            'customer_phone': '555-0199',
            'order_type': 'dine_in',
            'table_number': '5',
            'items': [
                {
                    'foodId': self.dish_a.id,
                    'quantity': 2,
                    'spiceLevel': 'Medium',
                    'unitPrice': 1.00, # Client attempt to tamper
                    'addons': [{'id': self.addon_a.id, 'price': 0.10}], # Client attempt to tamper
                }
            ]
        }

        resp = self.client.post(
            reverse('checkout_submit_api', args=[self.rest_a.slug]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        # Verify saved order
        order = Order.objects.get(order_number=data['order_number'])
        # Server subtotal must be: (15.00 + 3.00) * 2 = 36.00
        self.assertEqual(order.subtotal, Decimal('36.00'))
        # Tax at 5%: 36.00 * 0.05 = 1.80
        self.assertEqual(order.tax_amount, Decimal('1.80'))
        # Total: 37.80
        self.assertEqual(order.total_amount, Decimal('37.80'))
        self.assertEqual(order.table_identifier, '5')

    def test_unavailable_item_rejected_at_checkout(self):
        self.dish_a.is_available = False
        self.dish_a.save()

        payload = {
            'customer_name': 'John Doe',
            'customer_phone': '555-1111',
            'order_type': 'takeaway',
            'items': [{'foodId': self.dish_a.id, 'quantity': 1}]
        }

        resp = self.client.post(
            reverse('checkout_submit_api', args=[self.rest_a.slug]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data['success'])
        self.assertIn('sold out', data['error'].lower())

    # 4. QR and Table URL Verification
    def test_table_specific_qr_url(self):
        qr_url = self.table_a5.get_table_url()
        self.assertIn('/r/spice-garden/menu/?table=5', qr_url)

        resp = self.client.get(reverse('restaurant_menu', args=[self.rest_a.slug]) + '?table=5')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['table_valid'])
        self.assertContains(resp, 'Table 5')

    # 5. Full End-to-End Workflow Test
    def test_full_owner_customer_lifecycle(self):
        # Step 1: Owner logs in and creates a new item
        self.client.login(username='owner_a', password='Password123!')
        create_resp = self.client.post(reverse('owner_food_add'), {
            'name': 'Saffron Lamb Shank',
            'category': self.cat_a.id,
            'description': 'Slow braised lamb shank in rich saffron sauce',
            'price': '26.00',
            'spice_level': 'Spicy',
            'is_vegetarian': '',
            'is_available': 'on',
            'display_order': 5,
            'addon_names[]': ['Extra Gravy'],
            'addon_prices[]': ['3.50'],
        })
        self.assertEqual(create_resp.status_code, 302)

        new_food = FoodItem.objects.get(slug='saffron-lamb-shank', restaurant=self.rest_a)
        extra_gravy = new_food.addons.first()

        # Step 2: Customer logs out, scans QR table=5, views menu
        self.client.logout()
        menu_resp = self.client.get(reverse('restaurant_menu', args=[self.rest_a.slug]) + '?table=5')
        self.assertEqual(menu_resp.status_code, 200)
        self.assertContains(menu_resp, 'Saffron Lamb Shank')
        self.assertContains(menu_resp, '$26.00')

        # Step 3: Customer places order
        order_payload = {
            'customer_name': 'David Miller',
            'customer_phone': '+1 555-888-9999',
            'order_type': 'dine_in',
            'table_number': '5',
            'items': [
                {
                    'foodId': new_food.id,
                    'quantity': 1,
                    'spiceLevel': 'Spicy',
                    'specialInstructions': 'Extra well done',
                    'addons': [{'id': extra_gravy.id, 'price': 3.50}]
                }
            ]
        }
        order_resp = self.client.post(
            reverse('checkout_submit_api', args=[self.rest_a.slug]),
            data=json.dumps(order_payload),
            content_type='application/json'
        )
        self.assertEqual(order_resp.status_code, 200)
        order_info = order_resp.json()
        self.assertTrue(order_info['success'])

        order_obj = Order.objects.get(order_number=order_info['order_number'])
        self.assertEqual(order_obj.status, 'pending')

        # Step 4: Customer checks live tracking page
        status_resp = self.client.get(reverse('order_status', args=[self.rest_a.slug, order_obj.access_token]))
        self.assertEqual(status_resp.status_code, 200)
        self.assertContains(status_resp, 'Order Received!')
        self.assertContains(status_resp, 'Table 5')
        self.assertContains(status_resp, 'Saffron Lamb Shank')

        # Step 5: Owner logs in, sees order, and updates status to 'preparing'
        self.client.login(username='owner_a', password='Password123!')
        live_resp = self.client.get(reverse('owner_live_orders_api'))
        self.assertEqual(live_resp.status_code, 200)
        live_data = live_resp.json()
        self.assertGreaterEqual(live_data['pending_count'], 1)

        # Update order status
        update_resp = self.client.post(
            reverse('owner_order_update_status_api', args=[order_obj.id]),
            data=json.dumps({'status': 'preparing'}),
            content_type='application/json'
        )
        self.assertEqual(update_resp.status_code, 200)

        # Step 6: Customer polling reflects updated status
        poll_resp = self.client.get(reverse('order_status_api', args=[self.rest_a.slug, order_obj.access_token]))
        self.assertEqual(poll_resp.status_code, 200)
        self.assertEqual(poll_resp.json()['status'], 'preparing')
