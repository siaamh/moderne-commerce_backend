"""
Management command: seed_catalog

Seeds 5 brands, 5 root categories (each with 2 subcategories),
and 10 products spread across them.

Idempotent — already-existing slugs are skipped, not duplicated.

Usage:
    python manage.py seed_catalog
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta

from apps.products.models import Brand, Category, Discount, Product


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

BRANDS = [
    {
        "name": "AuraWear",
        "slug": "aurawear",
        "description": "Contemporary lifestyle apparel designed for everyday elegance.",
    },
    {
        "name": "Novex Tech",
        "slug": "novex-tech",
        "description": "Cutting-edge consumer electronics built for performance.",
    },
    {
        "name": "Terroir Home",
        "slug": "terroir-home",
        "description": "Thoughtfully crafted home goods rooted in natural materials.",
    },
    {
        "name": "Kinetic Sport",
        "slug": "kinetic-sport",
        "description": "Premium athletic gear engineered to push your limits.",
    },
    {
        "name": "Lumière Beauty",
        "slug": "lumiere-beauty",
        "description": "Luxury skincare and beauty products inspired by French cosmetics.",
    },
]

CATEGORIES = [
    {
        "name": "Clothing",
        "slug": "clothing",
        "description": "Explore our curated collection of contemporary fashion for every occasion.",
        "children": [
            {"name": "Men's Clothing", "slug": "mens-clothing"},
            {"name": "Women's Clothing", "slug": "womens-clothing"},
        ],
    },
    {
        "name": "Electronics",
        "slug": "electronics",
        "description": "The latest gadgets, devices and accessories for a connected life.",
        "children": [
            {"name": "Smartphones", "slug": "smartphones"},
            {"name": "Audio", "slug": "audio"},
        ],
    },
    {
        "name": "Home & Living",
        "slug": "home-living",
        "description": "Transform your space with our collection of home essentials and décor.",
        "children": [
            {"name": "Kitchen", "slug": "kitchen"},
            {"name": "Bedroom", "slug": "bedroom"},
        ],
    },
    {
        "name": "Sports & Fitness",
        "slug": "sports-fitness",
        "description": "Everything you need to stay active, from gym essentials to outdoor gear.",
        "children": [
            {"name": "Gym Equipment", "slug": "gym-equipment"},
            {"name": "Outdoor Sports", "slug": "outdoor-sports"},
        ],
    },
    {
        "name": "Beauty & Care",
        "slug": "beauty-care",
        "description": "Premium skincare, cosmetics and wellness products for your daily ritual.",
        "children": [
            {"name": "Skincare", "slug": "skincare"},
            {"name": "Fragrances", "slug": "fragrances"},
        ],
    },
]

PRODUCTS = [
    # Clothing
    {
        "name": "Classic Oxford Shirt",
        "slug": "classic-oxford-shirt",
        "description": (
            "A timeless Oxford shirt crafted from 100% premium cotton. "
            "Features a button-down collar, chest pocket, and a relaxed yet polished fit "
            "that transitions effortlessly from desk to dinner."
        ),
        "price": Decimal("1850.00"),
        "stock": 45,
        "category_slug": "mens-clothing",
        "brand_slug": "aurawear",
        "is_featured": True,
        "featured_order": 1,
    },
    {
        "name": "Linen Wrap Dress",
        "slug": "linen-wrap-dress",
        "description": (
            "Effortlessly chic wrap dress in breathable linen blend. "
            "The adjustable tie waist flatters every silhouette. "
            "Available in warm earth tones perfect for the season."
        ),
        "price": Decimal("2400.00"),
        "stock": 30,
        "category_slug": "womens-clothing",
        "brand_slug": "aurawear",
        "is_featured": True,
        "featured_order": 2,
        "discount": {
            "title": "Summer Style Sale",
            "description": "20% off selected women's clothing this weekend.",
            "discount_type": "percentage",
            "value": Decimal("20"),
        },
    },
    # Electronics
    {
        "name": "Novex ProBud Wireless Earbuds",
        "slug": "novex-probud-wireless-earbuds",
        "description": (
            "Active noise cancellation, 30-hour battery life, and IPX5 water resistance. "
            "Hi-Res certified audio with custom-tuned 10mm drivers. "
            "Includes fast-charge case — 10 minutes gives 2 hours of playback."
        ),
        "price": Decimal("4999.00"),
        "stock": 60,
        "category_slug": "audio",
        "brand_slug": "novex-tech",
        "is_featured": True,
        "featured_order": 3,
        "discount": {
            "title": "Launch Week Offer",
            "description": "৳500 off on all Novex audio products.",
            "discount_type": "fixed",
            "value": Decimal("500"),
        },
    },
    {
        "name": "Novex Slim S23 Smartphone",
        "slug": "novex-slim-s23-smartphone",
        "description": (
            "6.7-inch AMOLED display, 108MP triple camera system, and 5000mAh battery. "
            "Powered by the latest octa-core processor with 12GB RAM. "
            "Available in Midnight Black, Pearl White, and Ocean Blue."
        ),
        "price": Decimal("34999.00"),
        "stock": 20,
        "category_slug": "smartphones",
        "brand_slug": "novex-tech",
        "is_featured": True,
        "featured_order": 4,
    },
    # Home & Living
    {
        "name": "Artisan Pour-Over Coffee Set",
        "slug": "artisan-pour-over-coffee-set",
        "description": (
            "Hand-blown borosilicate glass dripper with matching carafe. "
            "Includes a precision-ground stainless steel filter for a clean, "
            "full-bodied cup every time. A centerpiece for the modern kitchen."
        ),
        "price": Decimal("2200.00"),
        "stock": 25,
        "category_slug": "kitchen",
        "brand_slug": "terroir-home",
        "is_featured": False,
    },
    {
        "name": "Organic Linen Duvet Cover",
        "slug": "organic-linen-duvet-cover",
        "description": (
            "OEKO-TEX certified 100% organic stone-washed linen. "
            "Naturally temperature-regulating, hypoallergenic and softer with every wash. "
            "Available in Queen, King and Super King. Colour: Natural Oat."
        ),
        "price": Decimal("3800.00"),
        "stock": 18,
        "category_slug": "bedroom",
        "brand_slug": "terroir-home",
        "is_featured": True,
        "featured_order": 5,
        "discount": {
            "title": "Home Refresh Sale",
            "description": "15% off all bedroom linen this week.",
            "discount_type": "percentage",
            "value": Decimal("15"),
        },
    },
    # Sports & Fitness
    {
        "name": "Kinetic Pro Resistance Band Set",
        "slug": "kinetic-pro-resistance-band-set",
        "description": (
            "Set of 5 latex-free resistance bands with fabric grip sleeves. "
            "Resistance levels: 10lb, 20lb, 30lb, 40lb, 50lb. "
            "Includes carry bag, door anchor, and foam handles for versatile training."
        ),
        "price": Decimal("1299.00"),
        "stock": 80,
        "category_slug": "gym-equipment",
        "brand_slug": "kinetic-sport",
        "is_featured": False,
    },
    {
        "name": "Trail Runner X7 Backpack",
        "slug": "trail-runner-x7-backpack",
        "description": (
            "28L hydration-compatible trail backpack built for long-distance runs and hikes. "
            "Features chest and hip straps, rain cover, reflective strips, "
            "and multiple zip compartments for gear organisation."
        ),
        "price": Decimal("5500.00"),
        "stock": 15,
        "category_slug": "outdoor-sports",
        "brand_slug": "kinetic-sport",
        "is_featured": True,
        "featured_order": 6,
    },
    # Beauty & Care
    {
        "name": "Lumière Radiance Serum",
        "slug": "lumiere-radiance-serum",
        "description": (
            "A concentrated brightening serum with 15% Vitamin C, niacinamide and hyaluronic acid. "
            "Clinically tested to visibly reduce dark spots in 4 weeks. "
            "Fragrance-free, dermatologist-approved formula for all skin types."
        ),
        "price": Decimal("2850.00"),
        "stock": 50,
        "category_slug": "skincare",
        "brand_slug": "lumiere-beauty",
        "is_featured": True,
        "featured_order": 7,
        "discount": {
            "title": "Beauty Week",
            "description": "৳300 off Lumière Radiance Serum.",
            "discount_type": "fixed",
            "value": Decimal("300"),
        },
    },
    {
        "name": "Lumière Velvet Noir Eau de Parfum",
        "slug": "lumiere-velvet-noir-edp",
        "description": (
            "An opulent oriental fragrance with top notes of bergamot and black pepper, "
            "a heart of oud and dark rose, and a base of sandalwood and musk. "
            "50ml. Handcrafted in Grasse, France."
        ),
        "price": Decimal("6500.00"),
        "stock": 12,
        "category_slug": "fragrances",
        "brand_slug": "lumiere-beauty",
        "is_featured": False,
    },
]


class Command(BaseCommand):
    help = "Seed 5 brands, 5 categories (with subcategories) and 10 products."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding catalog data...\n"))

        brands = self._seed_brands()
        categories = self._seed_categories()
        self._seed_products(brands, categories)

        self.stdout.write(self.style.SUCCESS("\nCatalog seeding complete."))

    # ------------------------------------------------------------------

    def _seed_brands(self) -> dict:
        brand_map = {}
        for data in BRANDS:
            obj, created = Brand.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "is_active": True,
                },
            )
            brand_map[data["slug"]] = obj
            status = self.style.SUCCESS("  CREATE") if created else "  SKIP  "
            self.stdout.write(f"{status} brand '{obj.name}'")
        return brand_map

    def _seed_categories(self) -> dict:
        category_map = {}
        for data in CATEGORIES:
            parent, created = Category.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "is_active": True,
                    "parent": None,
                },
            )
            category_map[data["slug"]] = parent
            status = self.style.SUCCESS("  CREATE") if created else "  SKIP  "
            self.stdout.write(f"{status} category '{parent.name}'")

            for child_data in data.get("children", []):
                child, child_created = Category.objects.get_or_create(
                    slug=child_data["slug"],
                    defaults={
                        "name": child_data["name"],
                        "is_active": True,
                        "parent": parent,
                    },
                )
                category_map[child_data["slug"]] = child
                c_status = self.style.SUCCESS("    CREATE") if child_created else "    SKIP  "
                self.stdout.write(f"{c_status} subcategory '{child.name}'")

        return category_map

    def _seed_products(self, brands: dict, categories: dict):
        for data in PRODUCTS:
            category = categories.get(data["category_slug"])
            brand = brands.get(data["brand_slug"])

            product, created = Product.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "price": data["price"],
                    "stock": data["stock"],
                    "category": category,
                    "brand": brand,
                    "is_active": True,
                    "is_featured": data.get("is_featured", False),
                    "featured_order": data.get("featured_order", 0),
                },
            )

            status = self.style.SUCCESS("  CREATE") if created else "  SKIP  "
            self.stdout.write(f"{status} product '{product.name}'")

            # Create a discount if specified and none already exists for this product.
            discount_data = data.get("discount")
            if discount_data and created:
                start = now()
                end = start + timedelta(days=7)

                existing = Discount.objects.filter(
                    product=product,
                    is_active=True,
                    starts_at__lt=end,
                    ends_at__gt=start,
                ).exists()

                if not existing:
                    Discount.objects.create(
                        product=product,
                        title=discount_data["title"],
                        description=discount_data["description"],
                        discount_type=discount_data["discount_type"],
                        value=discount_data["value"],
                        starts_at=start,
                        ends_at=end,
                        is_active=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"    + discount '{discount_data['title']}'")
                    )
