import time
import logging
import json
import random
import string
import pytz
from django.utils.translation import gettext as _

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import localtime
from weasyprint import HTML
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from .models import Client, Category, Product, Order, ProductVariant, ShippingCost, Commune, MainVariant, QuantityType, ProductVariant, OrderItem
from django.contrib import messages
from .forms import ClientUpdateForm  # Import the form from forms.py
from django.urls import reverse
import hashlib
from django.conf import settings
import requests
from django.http import JsonResponse
from .payment_service import SatimPayment
from django.core.mail import EmailMessage
from .forms import CustomSignUpForm
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.sites.shortcuts import get_current_site


def generate_order_number():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

logger = logging.getLogger(__name__)

@login_required
def home(request):
    categories = Category.objects.all()
    return render(request, 'index.html', {'categories': categories})


def signup_view(request):
    if request.method == "POST":
        form = CustomSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Client.objects.create(
                user=user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                number=form.cleaned_data['number'],
                adresse=form.cleaned_data['adresse']
            )
            login(request, user)
            return redirect("home")
    else:
        form = CustomSignUpForm()
    return render(request, "signup.html", {"form": form})


@login_required
def products(request):
    categories = Category.objects.prefetch_related('products').all()  # Optimized query


    return render(request, "products_page.html", {"categories": categories})

@login_required
def product_singlepage(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all()
    main_variants = product.main_variants.all().prefetch_related("quantity_types")

    return render(request, 'product_singlepage.html', {
        'product': product,
        'variants': variants,
        'main_variants': main_variants,
    })


@login_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)

        variant_id = request.POST.get("p_variant")
        main_variant_id = request.POST.get("main_variant")
        quantity_type_id = request.POST.get("quantity_type")
        quantity = request.POST.get("quantity")

        # Validate quantity
        if not quantity or not quantity.isdigit() or int(quantity) <= 0:
            messages.error(request, "Veuillez entrer une quantité valide.")
            return redirect("product_singlepage", product_id=product.id)
        quantity = int(quantity)

        if quantity > product.stock:
            messages.error(request, f"Désolé, seulement {product.stock} unité(s) disponible(s).")
            return redirect("product_singlepage", product_id=product.id)

        # Validate main variant
        if not main_variant_id:
            messages.error(request, "Veuillez sélectionner une contenance.")
            return redirect("product_singlepage", product_id=product.id)

        try:
            main_variant = MainVariant.objects.get(id=main_variant_id, product=product)
        except MainVariant.DoesNotExist:
            messages.error(request, "Contenance sélectionnée invalide.")
            return redirect("product_singlepage", product_id=product.id)

        # Validate quantity type
        if not quantity_type_id:
            messages.error(request, "Veuillez sélectionner un type de quantité.")
            return redirect("product_singlepage", product_id=product.id)

        try:
            quantity_type = QuantityType.objects.get(id=quantity_type_id, main_variant=main_variant)
        except QuantityType.DoesNotExist:
            messages.error(request, "Type de quantité invalide pour la contenance sélectionnée.")
            return redirect("product_singlepage", product_id=product.id)

        # Optional variant
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
            except ProductVariant.DoesNotExist:
                messages.error(request, "Variante sélectionnée invalide.")
                return redirect("product_singlepage", product_id=product.id)

        # Calculate total price
        total_units = quantity_type.unit_count * quantity
        base_price = quantity_type.price * total_units
        variant_price = variant.additional_price * total_units if variant else 0
        total_price = base_price + variant_price

        # Create the order
        order = Order.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            total_price=total_price,
            main_variant=main_variant,
            quantity_type=quantity_type,
            p_variant=variant,
            payment_status='en attente',
            unit_count=total_units
        )
        return redirect(reverse('confirm_order', args=[order.id]))

    return redirect("product_singlepage", product_id=product_id)


from django.views.decorators.http import require_http_methods

from django.http import JsonResponse
from .models import Commune

@login_required
def get_communes_for_wilaya(request):
    wilaya_code = request.GET.get("wilaya_code")
    communes = Commune.objects.filter(wilaya_code=wilaya_code).values_list("name", flat=True)
    return JsonResponse({"communes": list(communes)})


@login_required
@require_http_methods(["GET", "POST"])
def confirm_order(request, order_id):
    TRANSPORT_CHOICES = [
        ('léger', 'Léger'),
        ('lourd', 'Lourd'),
        ('semi', 'Semi'),
    ]
    WILAYA_CHOICES = [
        ("02", "Chlef"), ("03", "Laghouat"), ("04", "Oum El Bouaghi"),
        ("05", "Batna"), ("06", "Béjaïa"), ("07", "Biskra"),
        ("09", "Blida"), ("10", "Bouira"), ("12", "Tébessa"),
        ("13", "Tlemcen"), ("14", "Tiaret"), ("15", "Tizi Ouzou"),
        ("16", "Alger"), ("17", "Djelfa"), ("18", "Jijel"),
        ("19", "Sétif"), ("20", "Saïda"), ("21", "Skikda"),
        ("22", "Sidi Bel Abbès"), ("23", "Annaba"), ("24", "Guelma"),
        ("25", "Constantine"), ("26", "Médéa"), ("27", "Mostaganem"),
        ("28", "M'Sila"), ("29", "Mascara"), ("31", "Oran"),
        ("32", "El Bayadh"), ("34", "Bordj Bou Arréridj"), ("35", "Boumerdès"),
        ("36", "El Tarf"), ("38", "Tissemsilt"), ("39", "El Oued"),
        ("40", "Khenchela"), ("41", "Souk Ahras"), ("42", "Tipaza"),
        ("43", "Mila"), ("44", "Aïn Defla"), ("46", "Aïn Témouchent"),
        ("47", "Ghardaïa"), ("48", "Relizane"), ("51", "Ouled Djellal"),
        ("57", "El M'Ghair"),
    ]

    shipping_prices = ShippingCost.objects.select_related("commune").all()
    price_dict = {}
    for s in shipping_prices:
        if s.commune:
            key = f"{s.wilaya_code}-{s.commune.name}-{s.transport_type}"
        else:
            key = f"{s.wilaya_code}-{s.transport_type}"
        price_dict[key] = float(s.price)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == "POST":
        wilaya = request.POST.get("wilaya")
        transport_type = request.POST.get("transport_type")
        payment_method = request.POST.get("payment_method")
        captcha_response = request.POST.get("g-recaptcha-response")
        commune_name = request.POST.get("commune")

        order.commune = commune_name  # save commune name as plain text

        captcha_verify = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': settings.RECAPTCHA_SECRET_KEY, 'response': captcha_response}
        )
        captcha_result = captcha_verify.json()
        if not captcha_result.get('success'):
            messages.error(request, "Veuillez valider le CAPTCHA.")
            return redirect(request.path)

        commune_obj = Commune.objects.filter(name=commune_name, wilaya_code=wilaya).first() if commune_name else None

        if commune_obj:
            shipping = ShippingCost.objects.filter(
                wilaya_code=wilaya,
                commune=commune_obj,
                transport_type=transport_type
            ).first()
        else:
            shipping = ShippingCost.objects.filter(
                wilaya_code=wilaya,
                commune__isnull=True,
                transport_type=transport_type
            ).first()

        if not shipping:
            messages.error(request, "Le tarif de livraison est introuvable pour cette configuration.")
            return redirect('confirm_order', order_id=order.id)

        order.wilaya = wilaya
        order.transport_type = transport_type
        order.shipping_cost = shipping.price
        order.total_price += shipping.price
        order.save()

        if payment_method == "card":
            return redirect(reverse('initiate_payment', args=[order.id]))
        elif payment_method == "cod":

            messages.success(request, "Commande confirmée. Paiement à la livraison.")
            return render(request, 'payment/success_cod.html', {'order': order})
        else:
            messages.error(request, "Méthode de paiement invalide.")
            return redirect("confirm_order", order_id=order.id)

    return render(request, "payment/confirm_order.html", {
        "order": order,
        "WILAYA_CHOICES": WILAYA_CHOICES,
        "TRANSPORT_CHOICES": TRANSPORT_CHOICES,
        "shipping_prices_json": mark_safe(json.dumps(price_dict, cls=DjangoJSONEncoder)),
    })

from django.core.mail import send_mail
from django.contrib import messages
import logging
from django.conf import settings


@login_required
def confirm_cod_order(request, order_id):
    if request.method != 'POST':
        return redirect(reverse('confirm_order', args=[order_id]))

    try:
        order = get_object_or_404(Order, pk=order_id, user=request.user)
        user_id = order.user.id

        order.status = "en cours de traitement"
        order.save()

        subject = f"Confirmation de votre commande #{order.id}"

        message = f"""
        Bonjour {order.user.get_full_name() or order.user.username},
        
        Nous accusons réception de votre commande #{order.id} et vous remercions pour votre confiance.
        
        Détails de la commande :
        - Référence : #{order.id}
        - Montant total : {order.total_price} DA
        - Mode de paiement : Paiement à la livraison
        - Statut : En cours de traitement
        
        Votre commande sera traitée dans les plus brefs délais. Vous recevrez une notification lorsque votre colis sera expédié.
        
        Pour toute question, n'hésitez pas à répondre à cet email.
        
        Cordialement,
        L'équipe Le Carrefour de L'emballage
        """

        # Send email
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.client.email],
            fail_silently=False
        )

        messages.success(request, "La commande a été confirmée avec succès.")

        return redirect('orders', user_id=user_id)

    except Exception as e:
        logger.error(f"Error confirming order {order_id}: {str(e)}")
        messages.error(request, "Une erreur s'est produite lors de la confirmation.")
        return redirect(reverse('confirm_order', args=[order_id]))
@login_required
def orders(request, user_id):
    user_orders = Order.objects.filter(user_id=user_id)

    for order in user_orders:
        order.translated_status = _(order.payment_status)

    return render(request, 'orders.html', {'orders': user_orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def order_confirm_delete(request, order_id):
    # Get the order
    order = get_object_or_404(Order, id=order_id)
    user_id = order.user.id
    # Delete the order immediately
    order.delete()

    return redirect('orders', user_id=user_id)  # Make sure 'orders' is a valid URL name


@login_required
def profile(request, user_id):
    client = Client.objects.filter(user_id=user_id).first()  # Safely get Client object
    return render(request, 'profile.html', {'client': client})


@login_required
def profile_update(request):
    client, created = Client.objects.get_or_create(user=request.user)  # Ensure Client exists

    if request.method == 'POST':
        form = ClientUpdateForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile', user_id=request.user.id)
    else:
        form = ClientUpdateForm(instance=client)

    return render(request, 'profile_update.html', {'form': form})


def generate_signature(data_string, secret_key):
    """Adjust this depending on CIB requirements (SHA256 or MD5)."""
    return hashlib.sha256(f"{data_string}{secret_key}".encode()).hexdigest()





logger = logging.getLogger("ecommerce")

@csrf_exempt
def initiate_payment(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        amount = int(float(order.total_price) * 100)
        if amount < 5000:
            raise ValueError("Le montant doit être supérieur ou égal à 50 DZD")

        order_number = generate_order_number()
        udf1 = f"ORD{order.id:017d}"


        json_params = {
            "force_terminal_id": settings.SATIM_TERMINAL_ID,  # Must be in your settings
            "udf1": udf1,
            "client_name": f"{order.user.first_name} {order.user.last_name}",
            "client_phone": getattr(order.user.client, 'number', 'N/A'),

        }
        site = get_current_site(request)
        domain = f"https://{site.domain}"



        payload = {
            "userName": settings.SATIM_USERNAME,
            "password": settings.SATIM_PASSWORD,
            "orderNumber": order_number,
            "amount": amount,
            "currency": "012",
            "returnUrl": domain + reverse('payment_return'),
            "failUrl": domain + reverse('payment_fail'),
            "description": f"Commande #{order.id}",
            "language": "FR",
            "jsonParams": json.dumps(json_params)
        }

        logger.info("📦 Envoi de la requête d'enregistrement à SATIM...")
        logger.info(f"Payload sent to SATIM: {payload}") # Add this line
        response = requests.get(settings.SATIM_REGISTER_URL, params=payload, timeout=10)
        result = response.json()
        logger.info(f"🧾 Réponse SATIM: {result}")

        if "formUrl" in result:
            order.external_order_id = result["orderId"]
            order.order_number = order_number
            order.udf1 = udf1
            order.save()
            return redirect(result["formUrl"])
        else:
            return HttpResponse(f"❌ Erreur d'enregistrement : {result.get('errorMessage')}")

    except Order.DoesNotExist:
        return HttpResponse("❌ Commande non trouvée.")
    except Exception as e:
        logger.exception("Erreur lors de l'enregistrement de la commande")
        return HttpResponse(f"❌ Erreur interne : {str(e)}")





@csrf_exempt
def payment_return(request):
    order_id = request.GET.get('orderId')
    if not order_id:
        return JsonResponse({'status': 'error', 'message': 'Missing order ID'})

    confirm_params = {
        'userName': settings.SATIM_USERNAME,
        'password': settings.SATIM_PASSWORD,
        'orderId': order_id,
        'language': 'FR'
    }

    try:
        response = requests.get(settings.SATIM_CONFIRM_URL, params=confirm_params, timeout=10)
        result = response.json()

        if result.get('ErrorCode') == '0' and result.get('OrderStatus') == 2:
            # ✅ Successful payment
            try:
                order = Order.objects.get(external_order_id=order_id)
                order.payment_status = 'succés'
                order.payment_details = result
                order.payment_date = timezone.now()
                order.status = "en cours de traitement"
                order.save()
            except Order.DoesNotExist:
                order = None

            request.session['paid_order_id'] = order.id
            return redirect('payment_success_redirect')


        else:
            resp_code = result.get('params', {}).get('respCode')
            error_code = result.get('ErrorCode')
            order_status = result.get('OrderStatus')

        if resp_code == "00" and error_code == "0" and order_status == 3:
            message = "Votre transaction a été rejetée"
        else:
            message = result.get('params', {}).get('respCode_desc') or result.get('actionCodeDescription', "Le paiement a échoué")

        return render(request, 'payment/failed.html', {
            'error': message,
            'support_message': "En cas de problème de paiement, veuillez contacter le numéro vert de la SATIM 3020",
            'details': result
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Erreur lors de la confirmation de paiement',
            'details': str(e)
        })


def payment_success_redirect(request):
    order_id = request.session.get('paid_order_id')

    if not order_id:
        return render(request, "payment/success.html", {
            "error": "Aucune commande trouvée dans la session."
        })

    order = get_object_or_404(Order, id=order_id)

    algeria_tz = pytz.timezone('Africa/Algiers')
    payment_date = order.payment_date or timezone.now()
    localized_payment_date = payment_date.astimezone(algeria_tz)

    return render(request, "payment/success.html", {
        "order": order,
        "amount": order.total_price,
        "order_number": order.order_number,
        "transaction_id": order.external_order_id,
        "payment_date": localized_payment_date,  # ⬅️ THIS will fix the hour
        "approval_code": order.payment_details.get("approvalCode") or order.payment_details.get("params", {}).get("approvalCode"),
        "payment_type": "CIB" if order.payment_details.get("Pan", "").startswith("6280") else "Edahabia",
        "resp_message": order.payment_details.get("params", {}).get("respCode_desc", ""),
    })
@csrf_exempt
def payment_fail(request):
    order_id = request.GET.get('orderId')
    if not order_id:
        return render(request, 'payment/canceled.html')  # fallback to canceled if no info

    try:
        confirm_params = {
            'userName': settings.SATIM_USERNAME,
            'password': settings.SATIM_PASSWORD,
            'orderId': order_id,
            'language': 'FR'
        }

        response = requests.get(settings.SATIM_CONFIRM_URL, params=confirm_params, timeout=10)
        result = response.json()

        resp_code = result.get('params', {}).get('respCode')
        error_code = result.get('ErrorCode')
        order_status = result.get('OrderStatus')

        # 🟥 Cas rejet explicite (e.g. carte refusée)
        if resp_code == "00" and error_code == "0" and order_status == 3:
            message = "Votre transaction a été rejetée / Your transaction was rejected / تم رفض معاملتك"
        else:
            message = result.get('params', {}).get('respCode_desc') or result.get('actionCodeDescription', "Le paiement a échoué")

        try:
            order = Order.objects.get(external_order_id=order_id)
            order.payment_status = 'echoué'
            order.save()
        except Order.DoesNotExist:
            order = None

        return render(request, 'payment/failed.html', {
            'error': message,
            'support_message': "En cas de problème de paiement, veuillez contacter le numéro vert de la SATIM 3020",
            'details': result,
            'transaction_id': result.get("orderId")
        })

    except Exception as e:
        return render(request, 'payment/canceled.html')


from django.shortcuts import render

@csrf_exempt
def send_receipt_email(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)

        if not order.payment_details:
            return render(request, "payment/receipt_sent.html", {
                "status": "error",
                "message": "Aucun détail de paiement disponible."
            })

        recipient_email = None
        if hasattr(order.user, 'client') and getattr(order.user.client, 'email', None):
            recipient_email = order.user.client.email
        elif order.user.email:
            recipient_email = order.user.email

        if not recipient_email:
            return render(request, "payment/receipt_sent.html", {
                "status": "error",
                "message": "Aucune adresse email trouvée pour cet utilisateur."
            })
        algeria_tz = pytz.timezone('Africa/Algiers')
        payment_date = order.payment_date or timezone.now()
        localized_payment_date = payment_date.astimezone(algeria_tz)
        context = {
            'order': order,
            'details': order.payment_details,
            'transaction_id': order.external_order_id,
            'order_number': order.order_number,
            'approval_code': order.payment_details.get('approvalCode'),
            'amount': float(order.total_price),
            'currency': order.payment_details.get('currency', 'DZD'),
            'resp_message': order.payment_details.get('params', {}).get('respCode_desc', ''),
            'payment_type': "CIB" if order.payment_details.get("Pan", "").startswith("6280") else "Edahabia",
            'transaction_datetime': localized_payment_date,
        }

        try:
            html = render_to_string("payment/receipt_pdf.html", context)
            pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
        except Exception as pdf_error:
            return render(request, "payment/receipt_sent.html", {
                "status": "error",
                "message": f"Erreur lors de la génération du PDF : {pdf_error}"
            })

        email = EmailMessage(
            subject="Votre reçu de paiement",
            body="Veuillez trouver ci-joint le reçu de votre paiement.",
            from_email="contact@lecarrefouremballage.dz",
            to=[recipient_email]
        )
        email.attach(f"recu_commande_{order.id}.pdf", pdf, "application/pdf")

        try:
            email.send()
        except Exception as send_error:
            return render(request, "payment/receipt_sent.html", {
                "status": "error",
                "message": f"Erreur lors de l'envoi de l'email : {send_error}"
            })

        return render(request, "payment/receipt_sent.html", {
            "status": "success",
            "message": "Reçu envoyé avec succès."
        })

    except Exception as e:
        return render(request, "payment/receipt_sent.html", {
            "status": "error",
            "message": f"Erreur globale : {str(e)}"
        })



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
import pytz
from .models import Order

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    algeria_tz = pytz.timezone('Africa/Algiers')
    payment_date = order.payment_date or timezone.now()
    localized_payment_date = payment_date.astimezone(algeria_tz)

    client = getattr(order.user, 'client', None)
    payment_details = order.payment_details or {}
    payment_params = payment_details.get("params", {})
    steps = ["en attente", "en cours de traitement", "expédié", "livré"]

    context = {
        "order": order,
        "steps": steps,
        "amount": order.total_price,
        "order_number": order.order_number,
        "transaction_id": order.external_order_id,
        "payment_date": localized_payment_date,
        'payment_type': "CIB" if str(payment_details.get("Pan", "")).startswith("6280") else "Edahabia",
        "created_at": order.payment_date or order.order_date,
        "first_name": client.first_name if client else "",
        "last_name": client.last_name if client else "",
        "adresse": client.adresse if client else "",
        "cphonenumber": client.number if client else "",
    }

    return render(request, 'order_detail.html', context)

def download_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    payment_details = order.payment_details or {}
    payment_params = payment_details.get("params", {})

    client = getattr(order.user, 'client', None)

    context = {
        'order': order,
        'details': payment_details,
        'transaction_id': order.external_order_id or "N/A",
        'order_number': order.order_number,
        'approval_code': payment_details.get("approvalCode", "N/A"),
        'amount': order.total_price,
        'currency': payment_details.get("currency", "DZD"),
        'payment_type': "CIB" if str(payment_details.get("Pan", "")).startswith("6280") else "Edahabia",
        'transaction_datetime': order.payment_date or order.order_date,
        'resp_message': payment_params.get("respCode_desc", "Transaction details unavailable"),
        "first_name": client.first_name if client else "",
        "last_name": client.last_name if client else "",
        "adresse": client.adresse if client else "",
        "cphonenumber": client.number if client else "",
    }

    html_string = render_to_string("payment/receipt_pdf.html", context)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_commande_{order.id}.pdf"'
    return response