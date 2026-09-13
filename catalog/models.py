from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Seller(models.Model):
    class SellerType(models.TextChoices):
        ROASTER = "roaster", "Roaster"
        SHOP = "shop", "Shop"
        IMPORTER = "importer", "Importer"

    class Relationship(models.TextChoices):
        INDEXED = "indexed", "Indexed"
        PARTNER = "partner", "Partner"

    name = models.CharField(max_length=200, unique=True)
    seller_type = models.CharField(
        max_length=20, choices=SellerType.choices, default=SellerType.ROASTER
    )
    city = models.CharField(max_length=100, blank=True, default="")
    site_url = models.URLField(blank=True, default="")
    instagram = models.CharField(max_length=200, blank=True, default="")
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, default=Relationship.INDEXED
    )

    def __str__(self):
        return self.name


class BeanListing(models.Model):
    class Process(models.TextChoices):
        WASHED = "Washed", "Washed"
        NATURAL = "Natural", "Natural"
        HONEY = "Honey", "Honey"
        ANAEROBIC = "Anaerobic", "Anaerobic"
        OTHER = "Other", "Other"
        UNKNOWN = "Unknown", "Unknown"

    class RoastLevel(models.TextChoices):
        LIGHT = "Light", "Light"
        MEDIUM = "Medium", "Medium"
        DARK = "Dark", "Dark"
        UNKNOWN = "Unknown", "Unknown"

    class BeansFormat(models.TextChoices):
        WHOLE = "Whole bean", "Whole bean"
        GROUND = "Ground", "Ground"
        CAPSULE = "Capsule", "Capsule"
        POD = "Pods", "Pods"
        OTHER = "Other", "Other"

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="beans")
    name = models.CharField(max_length=200)
    origin = models.CharField(max_length=100, blank=True, null=True)
    variety = models.CharField(max_length=100, blank=True, null=True)
    process = models.CharField(max_length=20, choices=Process.choices, blank=True, null=True)
    roast_level = models.CharField(max_length=20, choices=RoastLevel.choices, blank=True, null=True)
    format = models.CharField(max_length=20, choices=BeansFormat.choices, blank=True, null=True)
    flavor_notes = models.TextField(blank=True, null=True)
    roasted_on = models.DateField(blank=True, null=True)
    weight_g = models.FloatField(blank=True, null=True)
    price_toman = models.BigIntegerField(blank=True, null=True)
    price_per_100g = models.FloatField(blank=True, null=True)
    specialty_score = models.FloatField(blank=True, null=True)
    in_stock = models.BooleanField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    last_verified = models.DateTimeField(blank=True, null=True)
    link = models.URLField(blank=True, default="", max_length=500)
    source_key = models.URLField(unique=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            GinIndex(fields=["name"], name="bean_name_trgm", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self):
        return self.name


class GearListing(models.Model):
    class GearCategory(models.TextChoices):
        GRINDER = "grinder", "Grinder"
        BREWER = "brewer", "Brewer"
        KETTLE = "kettle", "Kettle"
        FILTER = "filter", "Filter"
        ACCESSORY = "accessory", "Accessory"

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="gear")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=GearCategory.choices, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    key_specs = models.TextField(blank=True, null=True)
    price_toman = models.BigIntegerField(blank=True, null=True)
    in_stock = models.BooleanField(blank=True, null=True)
    last_crawled = models.DateTimeField(blank=True, null=True)
    link = models.URLField(blank=True, default="", max_length=500)
    source_key = models.URLField(unique=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            GinIndex(fields=["name"], name="gear_name_trgm", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self):
        return self.name