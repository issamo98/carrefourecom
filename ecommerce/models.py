from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.db.models import JSONField






class Client(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, help_text="Link to the Django user", null=True, blank=True
    )
    first_name = models.CharField(max_length=20, help_text="entrer votre prenom")
    last_name = models.CharField(max_length=20, help_text="entrer votre nom")
    email = models.EmailField()
    number = models.CharField(max_length=10, help_text="entrer votre numero de telephone")
    adresse = models.CharField(max_length=100, help_text="entrer votre BUSINESS Adresse", default="votre adresse ?")

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.last_name}, {self.first_name}'

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)


    def __str__(self):
        return self.name

AVAILABILITY_CHOICES = [
    ('en stock', 'En Stock'),
    ('rupture de stock', 'Rupture De Stock'),
]



class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    disponibility = models.CharField(
        max_length=30,
        choices=AVAILABILITY_CHOICES,
        blank=True,
        null=True,
        help_text="La disponibilité du produit",
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    def __str__(self):
        return self.name
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name}: {self.value} (+{self.additional_price} DA)"
class MainVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="main_variants")
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.product.name} - {self.value}"
class QuantityType(models.Model):
    main_variant = models.ForeignKey(MainVariant, on_delete=models.CASCADE, related_name="quantity_types")
    name = models.CharField(max_length=100)
    unit_count = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.main_variant.value} - {self.name} ({self.unit_count} units) - {self.price} / unité DA"


TRANSPORT_CHOICES = [
    ('léger', 'Léger'),
    ('lourd', 'Lourd'),
    ('semi', 'Semi'),
]

WILAYA_CHOICES = [
    ("02", "Chlef"),
    ("03", "Laghouat"),
    ("04", "Oum El Bouaghi"),
    ("05", "Batna"),
    ("06", "Béjaïa"),
    ("07", "Biskra"),
    ("09", "Blida"),
    ("10", "Bouira"),
    ("12", "Tébessa"),
    ("13", "Tlemcen"),
    ("14", "Tiaret"),
    ("15", "Tizi Ouzou"),
    ("16", "Alger"),
    ("17", "Djelfa"),
    ("18", "Jijel"),
    ("19", "Sétif"),
    ("20", "Saïda"),
    ("21", "Skikda"),
    ("22", "Sidi Bel Abbès"),
    ("23", "Annaba"),
    ("24", "Guelma"),
    ("25", "Constantine"),
    ("26", "Médéa"),
    ("27", "Mostaganem"),
    ("28", "M'Sila"),
    ("29", "Mascara"),
    ("31", "Oran"),
    ("32", "El Bayadh"),
    ("34", "Bordj Bou Arréridj"),
    ("35", "Boumerdès"),
    ("36", "El Tarf"),
    ("38", "Tissemsilt"),
    ("39", "El Oued"),
    ("40", "Khenchela"),
    ("41", "Souk Ahras"),
    ("42", "Tipaza"),
    ("43", "Mila"),
    ("44", "Aïn Defla"),
    ("46", "Aïn Témouchent"),
    ("47", "Ghardaïa"),
    ("48", "Relizane"),
    ("51", "Ouled Djellal"),
    ("57", "El M'Ghair"),
]

class Commune(models.Model):
    wilaya_code = models.CharField(max_length=2, choices=WILAYA_CHOICES)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.get_wilaya_code_display()})"

class ShippingCost(models.Model):
    wilaya_code = models.CharField(max_length=2, choices=WILAYA_CHOICES)
    commune = models.ForeignKey(Commune, on_delete=models.SET_NULL, null=True, blank=True)
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        loc = f"{self.get_wilaya_code_display()}"
        if self.commune:
            loc += f" - {self.commune.name}"
        return f"{loc} - {self.get_transport_type_display()} : {self.price} DA"

class Order(models.Model):
    STATUS_CHOICES = [
        ("en attente", "En attente"),
        ("en cours de traitement", "En cours de traitement"),
        ("expédié", "Expédié"),
        ("livrè", "Livré"),
        ("annulé", "Annulé")
    ]

    PAYMENT_STATUS_CHOICES = [
        ('en attente', 'En Attente'),
        ('avec succés', 'Avec Succés'),
        ('echoué', 'Echoué'),
        ('annuler', 'Annuler'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="orders")
    order_date = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="en attente")

    # New fields reflecting the new variant logic
    main_variant = models.ForeignKey(MainVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_type = models.ForeignKey(QuantityType, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)

    p_variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    external_order_id = models.CharField(max_length=100, null=True, blank=True)
    order_number = models.CharField(max_length=100, null=True, blank=True)

    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    wilaya = models.CharField(max_length=2, choices=WILAYA_CHOICES, null=True, blank=True)
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commune = models.CharField(max_length=100, null=True, blank=True)
    unit_count = models.PositiveIntegerField(null=True, blank=True)
    udf1 = models.CharField(max_length=20, blank=True, null=True)


    def __str__(self):
        client = getattr(self.user, 'client', None)
        client_info = f"{client.first_name} {client.last_name} - {client.number}" if client else "No Client Info"
        username = self.user.username if self.user else "Guest"
        product_name = self.product.name if self.product else "No Product"
        variant_info = f"- {self.p_variant.name} {self.p_variant.value}" if self.p_variant else ""
        main_var = self.main_variant.value if self.main_variant else "No Main Variant"
        qty_type = self.quantity_type.name if self.quantity_type else "No Quantity Type"
        return f"Order {self.id} - {username} - {client_info} - {product_name} - {main_var} - {qty_type} x {self.quantity} {variant_info}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.order.id}"





    




