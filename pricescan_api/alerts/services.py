import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction

from product.models import Offer, Product

from .models import Alert, AlertHistory, AlertType

logger = logging.getLogger(__name__)


class AlertService:
    """Сервис для работы с алертами"""

    @staticmethod
    def create_alert(
        user,
        product: Product,
        threshold_price: Decimal,
        currency: str = "RUB",
        shop=None,
        alert_type: str = AlertType.PRICE_DROP,
    ) -> Alert:
        """Создание нового алерта"""
        try:
            with transaction.atomic():
                alert = Alert.objects.create(
                    user=user,
                    product=product,
                    shop=shop,
                    threshold_price=threshold_price,
                    currency=currency,
                    alert_type=alert_type,
                )
                logger.info(f"Создан алерт {alert.id} для пользователя {user.id}")
                return alert
        except Exception as e:
            logger.error(f"Ошибка создания алерта: {e}")
            raise

    @staticmethod
    def check_alerts_for_product(product_id: int) -> Dict[str, int]:
        """Проверка алертов для конкретного продукта"""
        try:
            product = Product.objects.get(id=product_id)
            active_alerts = Alert.objects.filter(
                product=product, is_active=True
            ).select_related("user", "shop")

            if not active_alerts.exists():
                return {"checked": 0, "triggered": 0}

            triggered_count = 0

            for alert in active_alerts:
                try:
                    # Получаем текущие предложения
                    offers = Offer.objects.filter(product=product, is_available=True)

                    if alert.shop:
                        offers = offers.filter(shop=alert.shop)

                    if not offers.exists():
                        continue

                    # Проверяем условие срабатывания
                    if AlertService._should_trigger_alert(alert, offers):
                        AlertService._trigger_alert(alert, offers.first())
                        triggered_count += 1

                except Exception as e:
                    logger.error(f"Ошибка проверки алерта {alert.id}: {e}")
                    continue

            logger.info(
                f"Проверка алертов для продукта {product.title}: {triggered_count} сработало"
            )
            return {"checked": active_alerts.count(), "triggered": triggered_count}

        except Product.DoesNotExist:
            logger.error(f"Продукт с ID {product_id} не найден")
            return {"error": "Product not found"}
        except Exception as e:
            logger.error(f"Ошибка проверки алертов для продукта {product_id}: {e}")
            raise

    @staticmethod
    def check_all_alerts() -> Dict[str, int]:
        """Проверка всех активных алертов"""
        try:
            active_alerts = Alert.objects.filter(is_active=True).select_related(
                "product", "user", "shop"
            )

            triggered_count = 0
            checked_count = 0

            for alert in active_alerts:
                try:
                    checked_count += 1

                    # Получаем текущие предложения
                    offers = Offer.objects.filter(
                        product=alert.product, is_available=True
                    )

                    if alert.shop:
                        offers = offers.filter(shop=alert.shop)

                    if not offers.exists():
                        continue

                    # Проверяем условие срабатывания
                    if AlertService._should_trigger_alert(alert, offers):
                        AlertService._trigger_alert(alert, offers.first())
                        triggered_count += 1

                except Exception as e:
                    logger.error(f"Ошибка проверки алерта {alert.id}: {e}")
                    continue

            logger.info(
                f"Проверка всех алертов: {triggered_count} сработало из {checked_count}"
            )
            return {"checked": checked_count, "triggered": triggered_count}

        except Exception as e:
            logger.error(f"Ошибка проверки всех алертов: {e}")
            raise

    @staticmethod
    def _should_trigger_alert(alert: Alert, offers) -> bool:
        """Проверка условия срабатывания алерта"""
        if not offers.exists():
            return False

        if alert.alert_type == AlertType.PRICE_DROP:
            # Срабатывает, если есть предложения ниже порога
            return offers.filter(price__lte=alert.threshold_price).exists()

        elif alert.alert_type == AlertType.PRICE_RISE:
            # Срабатывает, если все предложения выше порога
            return not offers.filter(price__lt=alert.threshold_price).exists()

        elif alert.alert_type == AlertType.AVAILABILITY:
            # Срабатывает, если появились предложения в наличии
            return offers.filter(is_available=True).exists()

        return False

    @staticmethod
    def _trigger_alert(alert: Alert, offer: Offer):
        """Срабатывание алерта"""
        try:
            # Обновляем статус алерта
            alert.trigger()

            # Создаем запись в истории
            AlertHistory.objects.create(
                alert=alert,
                old_price=alert.threshold_price,  # Можно улучшить, сохраняя предыдущую цену
                new_price=offer.price,
                currency=offer.currency,
                shop=offer.shop,
                message=f"Цена {offer.price} {offer.currency} в магазине {offer.shop.name}",
            )

            logger.info(f"Алерт {alert.id} сработал для пользователя {alert.user.id}")

            # Здесь можно добавить отправку уведомления пользователю
            # через Telegram бот или email

        except Exception as e:
            logger.error(f"Ошибка срабатывания алерта {alert.id}: {e}")
            raise

    @staticmethod
    def get_user_alerts(user, limit: int = 10, offset: int = 0) -> List[Alert]:
        """Получение алертов пользователя с пагинацией"""
        return (
            Alert.objects.filter(user=user)
            .select_related("product", "shop")
            .order_by("-created_at")[offset : offset + limit]
        )

    @staticmethod
    def toggle_alert(alert_id: int, user) -> bool:
        """Переключение статуса алерта"""
        try:
            alert = Alert.objects.get(id=alert_id, user=user)
            alert.is_active = not alert.is_active
            alert.save(update_fields=["is_active"])
            return True
        except Alert.DoesNotExist:
            return False

    @staticmethod
    def delete_alert(alert_id: int, user) -> bool:
        """Удаление алерта"""
        try:
            alert = Alert.objects.get(id=alert_id, user=user)
            alert.delete()
            return True
        except Alert.DoesNotExist:
            return False

    @staticmethod
    def get_alert_statistics(user) -> Dict[str, Any]:
        """Статистика алертов пользователя"""
        alerts = Alert.objects.filter(user=user)

        return {
            "total_alerts": alerts.count(),
            "active_alerts": alerts.filter(is_active=True).count(),
            "triggered_alerts": alerts.filter(is_triggered=True).count(),
            "alerts_by_type": {
                alert_type: alerts.filter(alert_type=alert_type).count()
                for alert_type, _ in AlertType.choices
            },
        }
