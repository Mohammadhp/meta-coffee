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