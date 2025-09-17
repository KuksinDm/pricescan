from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Запускает все необходимые команды для инициализации проекта"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Начинаем инициализацию проекта...")
        
        # Создаем суперпользователя
        self.stdout.write("\n👤 Создание суперпользователя...")
        call_command('csu')
        
        # Импортируем ссылки
        self.stdout.write("\n📥 Импорт ссылок из CSV файлов...")
        call_command('import_links')

        # Импортируем прокси
        self.stdout.write("\n📥 Импорт прокси из CSV файлов...")
        call_command('import_proxies')

        # Импортируем аккаунты
        self.stdout.write("\n📥 Импорт аккаунтов из CSV файлов...")
        call_command('import_steam_accounts')
        
        self.stdout.write(self.style.SUCCESS("\n✨ Все команды успешно выполнены!"))