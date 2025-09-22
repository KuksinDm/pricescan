from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from product.models import Author, Category, Offer, Product, Shop

from .models import Alert, AlertHistory, AlertType
from .services import AlertService

User = get_user_model()


class AlertModelTest(TestCase):
    """Тесты для модели Alert"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            title="Test Product", author=self.author, category=self.category
        )
        self.shop = Shop.objects.create(
            name="Test Shop", domain="https://testshop.com", parser_type="beautifulsoup"
        )

    def test_create_alert(self):
        """Тест создания алерта"""
        alert = Alert.objects.create(
            user=self.user,
            product=self.product,
            shop=self.shop,
            threshold_price=Decimal("100.00"),
            currency="RUB",
            alert_type=AlertType.PRICE_DROP,
        )

        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.product, self.product)
        self.assertEqual(alert.threshold_price, Decimal("100.00"))
        self.assertTrue(alert.is_active)
        self.assertFalse(alert.is_triggered)

    def test_trigger_alert(self):
        """Тест срабатывания алерта"""
        alert = Alert.objects.create(
            user=self.user, product=self.product, threshold_price=Decimal("100.00")
        )

        initial_count = alert.trigger_count
        alert.trigger()

        self.assertTrue(alert.is_triggered)
        self.assertEqual(alert.trigger_count, initial_count + 1)
        self.assertIsNotNone(alert.last_triggered_at)


class AlertServiceTest(TestCase):
    """Тесты для AlertService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            title="Test Product", author=self.author, category=self.category
        )
        self.shop = Shop.objects.create(
            name="Test Shop", domain="https://testshop.com", parser_type="beautifulsoup"
        )

    def test_create_alert(self):
        """Тест создания алерта через сервис"""
        alert = AlertService.create_alert(
            user=self.user,
            product=self.product,
            threshold_price=Decimal("100.00"),
            currency="RUB",
            shop=self.shop,
        )

        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.product, self.product)
        self.assertEqual(alert.threshold_price, Decimal("100.00"))

    def test_check_alerts_for_product(self):
        """Тест проверки алертов для продукта"""
        # Создаем алерт
        Alert.objects.create(
            user=self.user, product=self.product, threshold_price=Decimal("100.00")
        )

        # Создаем предложение с ценой ниже порога
        Offer.objects.create(
            product=self.product,
            shop=self.shop,
            price=Decimal("90.00"),
            currency="RUB",
            is_available=True,
            url="https://testshop.com/product",
        )

        result = AlertService.check_alerts_for_product(self.product.id)

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["triggered"], 1)

    def test_get_alert_statistics(self):
        """Тест получения статистики алертов"""
        # Создаем несколько алертов
        Alert.objects.create(
            user=self.user,
            product=self.product,
            threshold_price=Decimal("100.00"),
            alert_type=AlertType.PRICE_DROP,
        )
        Alert.objects.create(
            user=self.user,
            product=self.product,
            threshold_price=Decimal("200.00"),
            alert_type=AlertType.PRICE_RISE,
        )

        stats = AlertService.get_alert_statistics(self.user)

        self.assertEqual(stats["total_alerts"], 2)
        self.assertEqual(stats["active_alerts"], 2)
        self.assertEqual(stats["alerts_by_type"]["price_drop"], 1)
        self.assertEqual(stats["alerts_by_type"]["price_rise"], 1)


class AlertHistoryTest(TestCase):
    """Тесты для истории алертов"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            title="Test Product", author=self.author, category=self.category
        )
        self.shop = Shop.objects.create(
            name="Test Shop", domain="https://testshop.com", parser_type="beautifulsoup"
        )
        self.alert = Alert.objects.create(
            user=self.user, product=self.product, threshold_price=Decimal("100.00")
        )

    def test_create_alert_history(self):
        """Тест создания записи в истории алертов"""
        history = AlertHistory.objects.create(
            alert=self.alert,
            old_price=Decimal("100.00"),
            new_price=Decimal("90.00"),
            currency="RUB",
            shop=self.shop,
            message="Цена снизилась",
        )

        self.assertEqual(history.alert, self.alert)
        self.assertEqual(history.new_price, Decimal("90.00"))
        self.assertIsNotNone(history.triggered_at)
