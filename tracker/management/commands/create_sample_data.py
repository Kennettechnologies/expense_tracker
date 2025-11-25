from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from tracker.models import (
    Profile, Category, Account, Transaction, Budget, 
    TransactionTemplate, SavingsGoal, GoalContribution, Bill
)


class Command(BaseCommand):
    help = 'Create sample data for testing Phase 2 features'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='Username for the test user (default: testuser)'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        # Create or get user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(f'Created user: {username}')
        else:
            self.stdout.write(f'Using existing user: {username}')
        
        # Create profile
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'currency': 'USD',
                'timezone': 'UTC'
            }
        )
        
        # Create categories
        categories_data = [
            'Food & Dining', 'Transportation', 'Shopping', 'Entertainment',
            'Bills & Utilities', 'Healthcare', 'Education', 'Travel',
            'Income', 'Investments', 'Gifts & Donations'
        ]
        
        categories = {}
        for cat_name in categories_data:
            category, _ = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = category
        
        # Create accounts
        accounts_data = [
            ('Checking Account', 'bank', 2500.00),
            ('Savings Account', 'bank', 5000.00),
            ('Credit Card', 'card', -450.00),
            ('Cash Wallet', 'cash', 150.00),
            ('M-Pesa', 'mobile', 75.00)
        ]
        
        accounts = {}
        for name, acc_type, balance in accounts_data:
            account, _ = Account.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    'account_type': acc_type,
                    'balance': Decimal(str(balance))
                }
            )
            accounts[name] = account
        
        # Create transaction templates
        templates_data = [
            ('Weekly Groceries', 'expense', 85.00, 'Food & Dining', 'Checking Account', 'Weekly grocery shopping', 'grocery,food,weekly'),
            ('Monthly Rent', 'expense', 1200.00, 'Bills & Utilities', 'Checking Account', 'Monthly rent payment', 'rent,housing,monthly'),
            ('Coffee Shop', 'expense', 4.50, 'Food & Dining', 'Cash Wallet', 'Daily coffee', 'coffee,daily,beverage'),
            ('Gas Station', 'expense', 45.00, 'Transportation', 'Credit Card', 'Fuel for car', 'gas,fuel,transportation'),
            ('Salary Deposit', 'income', 3500.00, 'Income', 'Checking Account', 'Monthly salary', 'salary,income,monthly'),
            ('Freelance Work', 'income', 500.00, 'Income', 'Checking Account', 'Freelance project payment', 'freelance,income,project')
        ]
        
        for name, trans_type, amount, cat_name, acc_name, desc, tags in templates_data:
            TransactionTemplate.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    'trans_type': trans_type,
                    'amount': Decimal(str(amount)),
                    'category': categories.get(cat_name),
                    'account': accounts.get(acc_name),
                    'description': desc,
                    'tags': tags,
                    'use_count': 0
                }
            )
        
        # Create savings goals
        goals_data = [
            ('Emergency Fund', 5000.00, 1200.00, date.today() + timedelta(days=365), 'Build 6-month emergency fund'),
            ('Vacation to Europe', 3000.00, 450.00, date.today() + timedelta(days=180), 'Summer vacation trip to Europe'),
            ('New Laptop', 1500.00, 800.00, date.today() + timedelta(days=90), 'MacBook Pro for work'),
            ('Car Down Payment', 8000.00, 2100.00, date.today() + timedelta(days=270), 'Down payment for new car')
        ]
        
        for name, target, current, target_date, desc in goals_data:
            goal, created = SavingsGoal.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    'target_amount': Decimal(str(target)),
                    'current_amount': Decimal(str(current)),
                    'target_date': target_date,
                    'description': desc,
                    'status': 'completed' if current >= target else 'active'
                }
            )
            
            if created and current > 0:
                # Create some contribution history
                contributions = [
                    (current * 0.4, 'Initial contribution'),
                    (current * 0.3, 'Monthly savings'),
                    (current * 0.3, 'Bonus money')
                ]
                
                for amount, desc in contributions:
                    if amount > 0:
                        GoalContribution.objects.create(
                            goal=goal,
                            amount=Decimal(str(amount)),
                            description=desc,
                            date=date.today() - timedelta(days=30)
                        )
        
        # Create bills
        bills_data = [
            ('Electric Bill', 120.00, 'Bills & Utilities', 'Checking Account', date.today() + timedelta(days=5), 'monthly', 'Monthly electricity bill', 3),
            ('Internet Service', 65.00, 'Bills & Utilities', 'Checking Account', date.today() + timedelta(days=12), 'monthly', 'Monthly internet service', 5),
            ('Phone Bill', 45.00, 'Bills & Utilities', 'Checking Account', date.today() + timedelta(days=8), 'monthly', 'Mobile phone service', 3),
            ('Car Insurance', 180.00, 'Transportation', 'Checking Account', date.today() + timedelta(days=25), 'monthly', 'Auto insurance premium', 7),
            ('Gym Membership', 35.00, 'Healthcare', 'Checking Account', date.today() + timedelta(days=15), 'monthly', 'Monthly gym membership', 2),
            ('Netflix Subscription', 15.99, 'Entertainment', 'Credit Card', date.today() + timedelta(days=3), 'monthly', 'Streaming service', 1),
            ('Overdue Credit Card', 250.00, 'Bills & Utilities', 'Checking Account', date.today() - timedelta(days=5), 'monthly', 'Credit card payment', 3)
        ]
        
        for name, amount, cat_name, acc_name, due_date, freq, desc, reminder_days in bills_data:
            status = 'overdue' if due_date < date.today() else 'pending'
            Bill.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    'amount': Decimal(str(amount)),
                    'category': categories.get(cat_name),
                    'account': accounts.get(acc_name),
                    'due_date': due_date,
                    'frequency': freq,
                    'status': status,
                    'description': desc,
                    'reminder_days': reminder_days,
                    'auto_pay': False
                }
            )
        
        # Create some sample transactions with tags
        transactions_data = [
            ('Grocery Store', 'expense', 78.50, 'Food & Dining', 'Checking Account', 'grocery,food,weekly', -2),
            ('Gas Station', 'expense', 42.00, 'Transportation', 'Credit Card', 'gas,fuel,car', -1),
            ('Coffee Shop', 'expense', 4.75, 'Food & Dining', 'Cash Wallet', 'coffee,beverage,daily', -1),
            ('Salary', 'income', 3500.00, 'Income', 'Checking Account', 'salary,income,monthly', -30),
            ('Freelance Project', 'income', 750.00, 'Income', 'Checking Account', 'freelance,income,web-design', -15),
            ('Restaurant Dinner', 'expense', 65.00, 'Food & Dining', 'Credit Card', 'restaurant,dinner,date', -3),
            ('Online Shopping', 'expense', 125.00, 'Shopping', 'Credit Card', 'shopping,clothes,online', -5),
            ('Movie Tickets', 'expense', 28.00, 'Entertainment', 'Cash Wallet', 'movie,entertainment,weekend', -7),
            ('Pharmacy', 'expense', 15.50, 'Healthcare', 'Checking Account', 'pharmacy,health,medicine', -4),
            ('Book Purchase', 'expense', 22.99, 'Education', 'Credit Card', 'books,education,learning', -10)
        ]
        
        for desc, trans_type, amount, cat_name, acc_name, tags, days_ago in transactions_data:
            Transaction.objects.get_or_create(
                user=user,
                description=desc,
                date=date.today() + timedelta(days=days_ago),
                defaults={
                    'trans_type': trans_type,
                    'amount': Decimal(str(amount)),
                    'category': categories.get(cat_name),
                    'account': accounts.get(acc_name),
                    'tags': tags
                }
            )
        
        # Create budgets
        budgets_data = [
            ('Monthly Food Budget', 'Food & Dining', 400.00),
            ('Transportation Budget', 'Transportation', 200.00),
            ('Entertainment Budget', 'Entertainment', 150.00),
            ('Shopping Budget', 'Shopping', 300.00)
        ]
        
        for name, cat_name, amount in budgets_data:
            Budget.objects.get_or_create(
                user=user,
                name=name,
                category=categories.get(cat_name),
                defaults={
                    'amount': Decimal(str(amount)),
                    'start_date': date.today().replace(day=1),
                    'end_date': date.today().replace(day=28)
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data for user: {username}\n'
                f'- Categories: {len(categories_data)}\n'
                f'- Accounts: {len(accounts_data)}\n'
                f'- Transaction Templates: {len(templates_data)}\n'
                f'- Savings Goals: {len(goals_data)}\n'
                f'- Bills: {len(bills_data)}\n'
                f'- Sample Transactions: {len(transactions_data)}\n'
                f'- Budgets: {len(budgets_data)}'
            )
        )
        
        self.stdout.write(
            self.style.WARNING(
                f'\nLogin credentials:\n'
                f'Username: {username}\n'
                f'Password: password123'
            )
        )
