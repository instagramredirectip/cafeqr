from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from ordering.models import (
    Restaurant, RestaurantStaff, MenuCategory, FoodItem,
    FoodAddon, DiningTable, Order, OrderItem, OrderItemAddon
)

class Command(BaseCommand):
    help = 'Seeds realistic sample data for multi-restaurant demonstration and testing.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample restaurants, categories, dishes, tables, and staff...")

        site_base = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')

        # 1. Superuser
        admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@dineflow.com'})
        admin_user.set_password('AdminPass123!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        # 2. Restaurant 1: Saffron & Sage
        r1, _ = Restaurant.objects.get_or_create(
            slug='saffron-sage',
            defaults={
                'name': 'Saffron & Sage Royal Kitchen',
                'tagline': 'Authentic Royal Flavors & Slow-Dum Specialties',
                'description': 'Award-winning heritage dining blending rich royal aromatics, clay-oven kebabs, and fragrant slow-cooked biryanis in an opulent warm atmosphere.',
                'phone': '+1 (555) 345-6789',
                'email': 'contact@saffronsage.com',
                'address': '742 Grand Boulevard, Suite 100, Metro City',
                'opening_hours': '11:30 AM - 11:00 PM',
                'currency_symbol': '$',
                'dine_in_enabled': True,
                'takeaway_enabled': True,
                'delivery_enabled': True,
                'tax_percentage': Decimal('5.00'),
                'delivery_fee': Decimal('3.50'),
                'minimum_order_amount': Decimal('15.00'),
                'is_active': True,
            }
        )
        r1.generate_general_qr(site_base)
        r1.save()

        # Staff for Restaurant 1
        u1, _ = User.objects.get_or_create(username='owner_saffron', defaults={'email': 'owner@saffronsage.com', 'first_name': 'Karthik', 'last_name': 'Rao'})
        u1.set_password('OwnerPass123!')
        u1.save()
        staff1, _ = RestaurantStaff.objects.get_or_create(user=u1, restaurant=r1, defaults={'role': 'owner'})

        # Categories for R1
        cat_starters, _ = MenuCategory.objects.get_or_create(
            restaurant=r1, slug='starters',
            defaults={'name': 'Clay Oven Starters', 'display_order': 1, 'description': 'Tender tandoor kebabs and crisped appetizers'}
        )
        cat_biryani, _ = MenuCategory.objects.get_or_create(
            restaurant=r1, slug='biryani-specials',
            defaults={'name': 'Dum Biryani Specialties', 'display_order': 2, 'description': 'Slow-cooked in sealed clay pots with aged basmati and saffron'}
        )
        cat_mains, _ = MenuCategory.objects.get_or_create(
            restaurant=r1, slug='curries-mains',
            defaults={'name': 'Heritage Curries & Mains', 'display_order': 3, 'description': 'Velvety gravies simmered with freshly ground spices'}
        )
        cat_desserts, _ = MenuCategory.objects.get_or_create(
            restaurant=r1, slug='desserts',
            defaults={'name': 'Artisan Desserts', 'display_order': 4, 'description': 'Traditional handcrafted confections'}
        )

        # Dishes for R1
        d1, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='murgh-malai-tikka',
            defaults={
                'category': cat_starters,
                'name': 'Murgh Malai Tikka',
                'description': 'Succulent chicken morsels marinated in fresh cream, cardamom, mild spices and charred to perfection in tandoor.',
                'price': Decimal('16.50'),
                'is_vegetarian': False,
                'spice_level': 'Mild',
                'is_available': True,
                'display_order': 1,
            }
        )
        FoodAddon.objects.get_or_create(food_item=d1, name='Extra Mint Chutney & Pickled Onions', defaults={'price': Decimal('1.50')})
        FoodAddon.objects.get_or_create(food_item=d1, name='Melted Garlic Butter Glaze', defaults={'price': Decimal('2.00')})

        d2, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='paneer-tikka-angara',
            defaults={
                'category': cat_starters,
                'name': 'Paneer Tikka Angara',
                'description': 'Cubes of fresh cottage cheese skewered with bell peppers, glazed with spicy tandoori marinade.',
                'price': Decimal('14.00'),
                'is_vegetarian': True,
                'spice_level': 'Spicy',
                'is_available': True,
                'display_order': 2,
            }
        )
        FoodAddon.objects.get_or_create(food_item=d2, name='Extra Cottage Cheese Skewer', defaults={'price': Decimal('4.00')})

        d3, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='hyderabadi-dum-biryani',
            defaults={
                'category': cat_biryani,
                'name': 'Royal Hyderabadi Dum Biryani',
                'description': 'Fragrant long-grain aged basmati rice layered with spiced marinated meat, caramelised onions, mint, and pure saffron.',
                'price': Decimal('22.00'),
                'is_vegetarian': False,
                'spice_level': 'Medium',
                'is_available': True,
                'display_order': 1,
            }
        )
        FoodAddon.objects.get_or_create(food_item=d3, name='Boiled Spiced Egg (2 pcs)', defaults={'price': Decimal('2.50')})
        FoodAddon.objects.get_or_create(food_item=d3, name='Burani Garlic Raita & Mirchi Salan', defaults={'price': Decimal('3.00')})
        FoodAddon.objects.get_or_create(food_item=d3, name='Double Caramelized Fried Onions', defaults={'price': Decimal('1.50')})

        d4, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='shahi-paneer-biryani',
            defaults={
                'category': cat_biryani,
                'name': 'Shahi Paneer Dum Biryani',
                'description': 'Slow-baked basmati rice pot with aromatic marinated paneer, garden vegetables, and rose essence.',
                'price': Decimal('18.50'),
                'is_vegetarian': True,
                'spice_level': 'Medium',
                'is_available': True,
                'display_order': 2,
            }
        )
        FoodAddon.objects.get_or_create(food_item=d4, name='Extra Roasted Cashews & Raisins', defaults={'price': Decimal('2.00')})

        d5, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='butter-chicken-delhi-style',
            defaults={
                'category': cat_mains,
                'name': 'Old Delhi Butter Chicken',
                'description': 'Slow-simmered tandoori chicken cooked in a velvety tomato and fenugreek butter gravy.',
                'price': Decimal('19.50'),
                'is_vegetarian': False,
                'spice_level': 'Mild',
                'is_available': True,
                'display_order': 1,
            }
        )
        FoodAddon.objects.get_or_create(food_item=d5, name='Truffle Butter Garlic Naan', defaults={'price': Decimal('4.50')})
        FoodAddon.objects.get_or_create(food_item=d5, name='Steamed Jeera Basmati Rice', defaults={'price': Decimal('3.50')})

        d6, _ = FoodItem.objects.get_or_create(
            restaurant=r1, slug='kesar-pistachio-kulfi',
            defaults={
                'category': cat_desserts,
                'name': 'Kesar Pistachio Matka Kulfi',
                'description': 'Traditional slow-reduced frozen milk dessert infused with saffron, green cardamom, and toasted pistachios.',
                'price': Decimal('8.00'),
                'is_vegetarian': True,
                'spice_level': 'None',
                'is_available': True,
                'display_order': 1,
            }
        )

        # Tables for R1
        for table_no in ['1', '2', '3', '5', '10']:
            t, _ = DiningTable.objects.get_or_create(
                restaurant=r1, table_number=table_no,
                defaults={'capacity': 4 if table_no != '5' else 8}
            )
            t.generate_qr(site_base)
            t.save()

        # 3. Restaurant 2: Bella Vista Trattoria
        r2, _ = Restaurant.objects.get_or_create(
            slug='bella-vista',
            defaults={
                'name': 'Trattoria Bella Vista',
                'tagline': 'Handmade Pasta & Neapolitan Woodfired Pizza',
                'description': 'Rustic Italian dining with authentic stone-ground wheat pasta, 48-hour fermented pizza dough, and cured cheeses.',
                'phone': '+1 (555) 890-1234',
                'email': 'ciao@bellavista.com',
                'address': '12 Ocean Breeze Way, Waterfront Harbor',
                'opening_hours': '12:00 PM - 10:30 PM',
                'currency_symbol': '$',
                'dine_in_enabled': True,
                'takeaway_enabled': True,
                'delivery_enabled': False,
                'tax_percentage': Decimal('6.00'),
                'delivery_fee': Decimal('0.00'),
                'minimum_order_amount': Decimal('10.00'),
                'is_active': True,
            }
        )
        r2.generate_general_qr(site_base)
        r2.save()

        # Staff for R2
        u2, _ = User.objects.get_or_create(username='owner_bella', defaults={'email': 'owner@bellavista.com', 'first_name': 'Marco', 'last_name': 'Rossi'})
        u2.set_password('OwnerPass123!')
        u2.save()
        staff2, _ = RestaurantStaff.objects.get_or_create(user=u2, restaurant=r2, defaults={'role': 'owner'})

        # Categories for R2
        cat_pizza, _ = MenuCategory.objects.get_or_create(
            restaurant=r2, slug='woodfired-pizza',
            defaults={'name': 'Woodfired Neapolitan Pizza', 'display_order': 1}
        )
        cat_pasta, _ = MenuCategory.objects.get_or_create(
            restaurant=r2, slug='handcrafted-pasta',
            defaults={'name': 'Handcrafted Pasta', 'display_order': 2}
        )

        dp1, _ = FoodItem.objects.get_or_create(
            restaurant=r2, slug='margherita-di-bufala',
            defaults={
                'category': cat_pizza,
                'name': 'Margherita di Bufala',
                'description': 'San Marzano tomatoes, buffalo mozzarella DOP, fresh basil leaves, extra virgin olive oil.',
                'price': Decimal('17.00'),
                'is_vegetarian': True,
                'spice_level': 'None',
                'is_available': True,
                'display_order': 1,
            }
        )
        FoodAddon.objects.get_or_create(food_item=dp1, name='Extra Burrata Core', defaults={'price': Decimal('4.50')})
        FoodAddon.objects.get_or_create(food_item=dp1, name='Hot Honey Drizzle', defaults={'price': Decimal('1.50')})

        # Tables for R2
        for table_no in ['1', '2', 'Patio-A']:
            t, _ = DiningTable.objects.get_or_create(
                restaurant=r2, table_number=table_no,
                defaults={'capacity': 4}
            )
            t.generate_qr(site_base)
            t.save()

        self.stdout.write(self.style.SUCCESS("Sample data successfully seeded!"))
        self.stdout.write(self.style.SUCCESS(f"R1: Saffron & Sage (http://127.0.0.1:8000/r/saffron-sage/menu/)"))
        self.stdout.write(self.style.SUCCESS(f"R2: Bella Vista (http://127.0.0.1:8000/r/bella-vista/menu/)"))
        self.stdout.write(self.style.SUCCESS("Owner Login: /owner/login/ (Users: owner_saffron, owner_bella / Pwd: OwnerPass123!)"))

