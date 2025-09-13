import requests
import logging
from django.conf import settings
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class SatimPayment:
    @staticmethod
    def register_order(order):
        """Step 1: Register order with SATIM"""
        amount = int(float(order.total_price) * 100)  # Convert to centimes

        params = {
            'userName': settings.SATIM_CONFIG['USERNAME'],
            'password': settings.SATIM_CONFIG['PASSWORD'],
            'terminalId': settings.SATIM_CONFIG['TERMINAL_ID'],
            'orderNumber': f"ORDER-{order.id}-{order.order_date.timestamp()}",
            'amount': amount,
            'currency': settings.SATIM_CONFIG['CURRENCY'],
            'returnUrl': settings.SATIM_CONFIG['RETURN_URL'],
            'failUrl': settings.SATIM_CONFIG['FAIL_URL'],
            'language': settings.SATIM_CONFIG['LANGUAGE'],
            'description': f"Payment for Order #{order.id}",
        }

        try:
            response = requests.get(
                settings.SATIM_CONFIG['REGISTER_URL'],
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SATIM registration failed: {str(e)}")
            raise

    @staticmethod
    def confirm_order(order_id):
        params = {
            'userName': settings.SATIM_CONFIG['USERNAME'],
            'password': settings.SATIM_CONFIG['PASSWORD'],
            'terminalId': settings.SATIM_CONFIG['TERMINAL_ID'],
            'orderId': order_id,
            'language': settings.SATIM_CONFIG['LANGUAGE'],
        }

        try:
            response = requests.get(
                settings.SATIM_CONFIG['CONFIRM_URL'],
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SATIM confirmation failed: {str(e)}")
            raise