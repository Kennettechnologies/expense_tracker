from django.core.management.base import BaseCommand
from tracker.models import Category


class Command(BaseCommand):
    help = 'Create default expense and income categories'

    def handle(self, *args, **options):
        # Check if categories already exist
        if Category.objects.exists():
            self.stdout.write(
                self.style.WARNING('Categories already exist. Skipping creation.')
            )
            return

        # Default expense categories
        expense_categories = [
            {'name': 'Food & Dining', 'color': '#FF6B6B', 'icon': 'fas fa-utensils'},
            {'name': 'Transportation', 'color': '#4ECDC4', 'icon': 'fas fa-car'},
            {'name': 'Shopping', 'color': '#45B7D1', 'icon': 'fas fa-shopping-bag'},
            {'name': 'Entertainment', 'color': '#96CEB4', 'icon': 'fas fa-film'},
            {'name': 'Bills & Utilities', 'color': '#FFEAA7', 'icon': 'fas fa-file-invoice'},
            {'name': 'Healthcare', 'color': '#DDA0DD', 'icon': 'fas fa-heartbeat'},
            {'name': 'Education', 'color': '#98D8C8', 'icon': 'fas fa-graduation-cap'},
            {'name': 'Travel', 'color': '#F7DC6F', 'icon': 'fas fa-plane'},
            {'name': 'Home & Garden', 'color': '#BB8FCE', 'icon': 'fas fa-home'},
            {'name': 'Personal Care', 'color': '#85C1E9', 'icon': 'fas fa-spa'},
            {'name': 'Insurance', 'color': '#F8C471', 'icon': 'fas fa-shield-alt'},
            {'name': 'Gifts & Donations', 'color': '#F1948A', 'icon': 'fas fa-gift'},
            {'name': 'Business', 'color': '#AED6F1', 'icon': 'fas fa-briefcase'},
            {'name': 'Other Expenses', 'color': '#D5DBDB', 'icon': 'fas fa-ellipsis-h'},
        ]

        # Default income categories
        income_categories = [
            {'name': 'Salary', 'color': '#1DD1A1', 'icon': 'fas fa-money-bill-wave'},
            {'name': 'Freelance', 'color': '#55EFC4', 'icon': 'fas fa-laptop'},
            {'name': 'Business Income', 'color': '#00B894', 'icon': 'fas fa-chart-line'},
            {'name': 'Investment Returns', 'color': '#00CEC9', 'icon': 'fas fa-chart-pie'},
            {'name': 'Rental Income', 'color': '#81ECEC', 'icon': 'fas fa-building'},
            {'name': 'Bonus', 'color': '#74B9FF', 'icon': 'fas fa-star'},
            {'name': 'Gift Received', 'color': '#A29BFE', 'icon': 'fas fa-gift'},
            {'name': 'Refund', 'color': '#FD79A8', 'icon': 'fas fa-undo'},
            {'name': 'Other Income', 'color': '#FDCB6E', 'icon': 'fas fa-plus-circle'},
        ]

        # Create expense categories
        created_count = 0
        for cat_data in expense_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'color': cat_data['color'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created expense category: {category.name}")

        # Create income categories
        for cat_data in income_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'color': cat_data['color'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created income category: {category.name}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} categories!')
        )
