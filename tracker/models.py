from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Count, Avg


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    timezone = models.CharField(max_length=64, default='UTC')
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    color = models.CharField(max_length=7, blank=True)
    icon = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Account(models.Model):
    ACCOUNT_TYPES = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('card', 'Card'),
        ('mobile', 'Mobile Money'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='cash')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Transaction(models.Model):
    TRAN_TYPES = (
        ('expense', 'Expense'),
        ('income', 'Income'),
        ('transfer', 'Transfer'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    account = models.ForeignKey(Account, null=True, blank=True, related_name='transactions', on_delete=models.SET_NULL)
    transfer_account = models.ForeignKey(Account, null=True, blank=True, related_name='incoming_transfers', on_delete=models.SET_NULL)
    trans_type = models.CharField(max_length=10, choices=TRAN_TYPES, default='expense', db_index=True)
    date = models.DateField(default=timezone.now, db_index=True)
    time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    tags = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'trans_type']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['date', 'trans_type']),
        ]
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.trans_type} {self.amount} - {self.user.username}"

    def save(self, *args, **kwargs):
        # Get the old transaction data before saving
        old = None
        if self.pk:
            try:
                old = Transaction.objects.get(pk=self.pk)
                # Make a copy of the old values before they're overwritten
                old_amount = old.amount
                old_trans_type = old.trans_type
                old_account = old.account
                old_transfer_account = old.transfer_account
            except Transaction.DoesNotExist:
                old = None

        # If this is an update, reverse the old transaction's effect
        if old:
            # Temporarily restore old values to properly reverse the transaction
            current_amount = self.amount
            current_trans_type = self.trans_type
            current_account = self.account
            current_transfer_account = self.transfer_account
            
            # Set old values for reversal
            self.amount = old_amount
            self.trans_type = old_trans_type
            self.account = old_account
            self.transfer_account = old_transfer_account
            
            # Reverse the old transaction
            self._apply_balance_change(reverse=True)
            
            # Restore new values
            self.amount = current_amount
            self.trans_type = current_trans_type
            self.account = current_account
            self.transfer_account = current_transfer_account

        # Save the transaction with the new data
        super().save(*args, **kwargs)

        # Apply the new transaction's effect
        self._apply_balance_change(reverse=False)

    def delete(self, *args, **kwargs):
        # reverse balance changes then delete
        self._apply_balance_change(reverse=True)
        super().delete(*args, **kwargs)

    def _apply_balance_change(self, reverse=False):
        # reverse==True -> undo the transaction
        from decimal import Decimal
        mul = -1 if reverse else 1
        amount_decimal = Decimal(str(self.amount))
        
        if self.trans_type == 'income' and self.account:
            self.account.balance += mul * amount_decimal
            self.account.save()
        elif self.trans_type == 'expense' and self.account:
            self.account.balance -= mul * amount_decimal
            self.account.save()
        elif self.trans_type == 'transfer' and self.account and self.transfer_account:
            # subtract from source, add to destination
            self.account.balance -= mul * amount_decimal
            self.account.save()
            self.transfer_account.balance += mul * amount_decimal
            self.transfer_account.save()


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class RecurringTransaction(models.Model):
    FREQUENCY = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    trans_type = models.CharField(max_length=10, choices=Transaction.TRAN_TYPES, default='expense')
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=200, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY, default='monthly')
    next_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recurring {self.trans_type} {self.amount} ({self.frequency}) - {self.user.username}"


class TransactionSplit(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='splits', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Split {self.amount} for {self.transaction}"


class TransactionTemplate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    trans_type = models.CharField(max_length=10, choices=Transaction.TRAN_TYPES, default='expense')
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=200, blank=True)
    use_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def create_transaction(self):
        """Create a transaction from this template"""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=self.amount,
            category=self.category,
            account=self.account,
            trans_type=self.trans_type,
            description=self.description,
            tags=self.tags,
            date=timezone.now().date()
        )
        self.use_count += 1
        self.save()
        return transaction


class SavingsGoal(models.Model):
    GOAL_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=GOAL_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def progress_percentage(self):
        if self.target_amount > 0:
            return min(100, (self.current_amount / self.target_amount) * 100)
        return 0

    @property
    def remaining_amount(self):
        return max(0, self.target_amount - self.current_amount)

    def add_contribution(self, amount):
        """Add money to the goal"""
        self.current_amount += amount
        if self.current_amount >= self.target_amount and self.status == 'active':
            self.status = 'completed'
            self.completed_at = timezone.now()
        self.save()


class GoalContribution(models.Model):
    goal = models.ForeignKey(SavingsGoal, related_name='contributions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} to {self.goal.name}"


class Bill(models.Model):
    BILL_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    )
    
    FREQUENCY_CHOICES = (
        ('once', 'One-time'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    due_date = models.DateField()
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    status = models.CharField(max_length=10, choices=BILL_STATUS, default='pending')
    description = models.TextField(blank=True)
    reminder_days = models.IntegerField(default=3)  # Days before due date to remind
    auto_pay = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - Due: {self.due_date}"

    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status == 'pending'

    @property
    def days_until_due(self):
        return (self.due_date - timezone.now().date()).days

    def mark_as_paid(self):
        """Mark bill as paid and create transaction"""
        self.status = 'paid'
        self.save()
        
        # Create transaction
        Transaction.objects.create(
            user=self.user,
            amount=self.amount,
            category=self.category,
            account=self.account,
            trans_type='expense',
            description=f"Bill payment: {self.name}",
            date=timezone.now().date()
        )
        
        # Generate next bill if recurring
        if self.frequency != 'once':
            self._create_next_bill()

    def _create_next_bill(self):
        """Create the next recurring bill"""
        from dateutil.relativedelta import relativedelta
        
        next_due_date = self.due_date
        if self.frequency == 'weekly':
            next_due_date += timezone.timedelta(weeks=1)
        elif self.frequency == 'monthly':
            next_due_date += relativedelta(months=1)
        elif self.frequency == 'quarterly':
            next_due_date += relativedelta(months=3)
        elif self.frequency == 'yearly':
            next_due_date += relativedelta(years=1)
        
        Bill.objects.create(
            user=self.user,
            name=self.name,
            amount=self.amount,
            category=self.category,
            account=self.account,
            due_date=next_due_date,
            frequency=self.frequency,
            description=self.description,
            reminder_days=self.reminder_days,
            auto_pay=self.auto_pay
        )


class FinancialHealthScore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)  # 0-100
    savings_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    budget_adherence = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    emergency_fund_months = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    debt_to_income_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_calculated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Score: {self.score}"
    
    def calculate_score(self):
        """Calculate financial health score based on various factors"""
        from decimal import Decimal
        
        # Get user's financial data
        total_income = Transaction.objects.filter(
            user=self.user, 
            trans_type='income',
            date__month=timezone.now().month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        total_expenses = Transaction.objects.filter(
            user=self.user, 
            trans_type='expense',
            date__month=timezone.now().month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        total_balance = Account.objects.filter(user=self.user).aggregate(
            Sum('balance'))['balance__sum'] or Decimal('0')
        
        # Calculate metrics
        if total_income > 0:
            self.savings_rate = ((total_income - total_expenses) / total_income) * 100
            monthly_expenses = total_expenses if total_expenses > 0 else Decimal('1')
            self.emergency_fund_months = total_balance / monthly_expenses
        
        # Calculate budget adherence
        budgets = Budget.objects.filter(user=self.user)
        if budgets.exists():
            adherence_scores = []
            for budget in budgets:
                spent = Transaction.objects.filter(
                    user=self.user,
                    category=budget.category,
                    trans_type='expense',
                    date__gte=budget.start_date or timezone.now().date().replace(day=1)
                ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
                
                if budget.amount > 0:
                    adherence = max(0, 100 - ((spent / budget.amount) * 100))
                    adherence_scores.append(adherence)
            
            if adherence_scores:
                self.budget_adherence = sum(adherence_scores) / len(adherence_scores)
        
        # Calculate overall score (weighted average)
        score = 0
        if self.savings_rate >= 20:
            score += 30
        elif self.savings_rate >= 10:
            score += 20
        elif self.savings_rate >= 0:
            score += 10
        
        if self.emergency_fund_months >= 6:
            score += 25
        elif self.emergency_fund_months >= 3:
            score += 15
        elif self.emergency_fund_months >= 1:
            score += 10
        
        if self.budget_adherence >= 90:
            score += 25
        elif self.budget_adherence >= 75:
            score += 20
        elif self.budget_adherence >= 50:
            score += 15
        
        # Bonus points for having multiple accounts and goals
        if Account.objects.filter(user=self.user).count() >= 3:
            score += 10
        
        if SavingsGoal.objects.filter(user=self.user, status='active').count() >= 1:
            score += 10
        
        self.score = min(100, score)
        self.save()
        return self.score


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('budget_alert', 'Budget Alert'),
        ('bill_reminder', 'Bill Reminder'),
        ('goal_milestone', 'Goal Milestone'),
        ('unusual_spending', 'Unusual Spending'),
        ('monthly_summary', 'Monthly Summary'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class BudgetAlert(models.Model):
    ALERT_TYPES = (
        ('50_percent', '50% Budget Used'),
        ('75_percent', '75% Budget Used'),
        ('90_percent', '90% Budget Used'),
        ('100_percent', 'Budget Exceeded'),
    )
    
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPES)
    triggered_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['budget', 'alert_type']
    
    def __str__(self):
        return f"{self.budget.name} - {self.get_alert_type_display()}"


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    budget_alerts = models.BooleanField(default=True)
    bill_reminders = models.BooleanField(default=True)
    monthly_reports = models.BooleanField(default=True)
    goal_notifications = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default='en')
    date_format = models.CharField(max_length=20, default='%Y-%m-%d')
    number_format = models.CharField(max_length=10, default='en-US')
    
    def __str__(self):
        return f"{self.user.username} Preferences"
