from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from .forms import (SignUpForm, ProfileForm, TransactionForm, CSVUploadForm, BudgetForm, 
                   RecurringTransactionForm, TransactionSplitForm, TransactionTemplateForm,
                   SavingsGoalForm, GoalContributionForm, BillForm, AdvancedSearchForm, BulkTransactionForm)
from .models import (Profile, Transaction, Category, Account, Budget, RecurringTransaction, 
                    TransactionSplit, TransactionTemplate, SavingsGoal, GoalContribution, Bill)
import csv
from io import TextIOWrapper
from django.utils import timezone
from datetime import date


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})


@login_required
def profile(request):
    profile = getattr(request.user, 'profile', None)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profile.html', {'form': form})


@login_required
def transactions(request):
    qs = Transaction.objects.filter(user=request.user).order_by('-date', '-time')

    # filters
    q = request.GET.get('q')
    cat = request.GET.get('category')
    ttype = request.GET.get('type')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    min_amt = request.GET.get('min')
    max_amt = request.GET.get('max')

    if q:
        qs = qs.filter(description__icontains=q)
    if cat:
        qs = qs.filter(category__id=cat)
    if ttype:
        qs = qs.filter(trans_type=ttype)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if min_amt:
        try:
            qs = qs.filter(amount__gte=float(min_amt))
        except Exception:
            pass
    if max_amt:
        try:
            qs = qs.filter(amount__lte=float(max_amt))
        except Exception:
            pass
    return render(request, 'transactions.html', {'transactions': qs})


@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            t = form.save(commit=False)
            t.user = request.user
            t.save()
            messages.success(request, 'Transaction added.')
            return redirect('transactions')
    else:
        form = TransactionForm()
    return render(request, 'transaction_form.html', {'form': form})


@login_required
def transaction_duplicate(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        t.pk = None
        t.created_at = timezone.now()
        t.updated_at = timezone.now()
        t.save()
        messages.success(request, 'Transaction duplicated.')
        return redirect('transactions')
    return render(request, 'transaction_confirm_delete.html', {'object': t, 'duplicate': True})


@login_required
def transaction_edit(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, instance=t)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated.')
            return redirect('transactions')
    else:
        form = TransactionForm(instance=t)
    splits = t.splits.all()
    return render(request, 'transaction_form.html', {'form': form, 'edit': True, 'transaction': t, 'splits': splits})


@login_required
def transaction_delete(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        t.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('transactions')
    return render(request, 'transaction_confirm_delete.html', {'object': t})


@login_required
def export_transactions_csv(request):
    qs = Transaction.objects.filter(user=request.user).order_by('-date')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=transactions.csv'
    writer = csv.writer(response)
    # include split rows after their parent transaction
    writer.writerow(['date', 'time', 'type', 'amount', 'category', 'account', 'description', 'tags', 'parent_id', 'is_split', 'split_category', 'split_amount'])
    for t in qs:
        writer.writerow([t.date, t.time, t.trans_type, t.amount, t.category and t.category.name, t.account and t.account.name, t.description, t.tags, '', '0', '', ''])
        for s in t.splits.all():
            writer.writerow([t.date, t.time, '', '', '', '', '', '', t.pk, '1', s.category and s.category.name, s.amount])
    return response


@login_required
def import_transactions_csv(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = TextIOWrapper(request.FILES['file'].file, encoding='utf-8')
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    t = Transaction(
                        user=request.user,
                        amount=row.get('amount', 0) or 0,
                        date=row.get('date') or date.today(),
                        description=row.get('description', ''),
                        trans_type=row.get('type', 'expense'),
                    )
                    cat_name = row.get('category')
                    if cat_name:
                        cat, _ = Category.objects.get_or_create(name=cat_name)
                        t.category = cat
                    t.save()
                    count += 1
                except Exception:
                    continue
            messages.success(request, f'Imported {count} transactions.')
            return redirect('transactions')
    else:
        form = CSVUploadForm()
    return render(request, 'import_csv.html', {'form': form})


@login_required
def dashboard(request):
    from datetime import timedelta
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
    from decimal import Decimal
    
    today = timezone.now().date()
    start_month = today.replace(day=1)
    last_month_start = (start_month - timedelta(days=1)).replace(day=1)
    last_month_end = start_month - timedelta(days=1)
    
    # Current month transactions
    trans = Transaction.objects.filter(user=request.user, date__gte=start_month, date__lte=today)
    income = trans.filter(trans_type='income').aggregate(total=Sum('amount'))['total'] or 0
    expenses = trans.filter(trans_type='expense').aggregate(total=Sum('amount'))['total'] or 0
    net = income - expenses
    
    # Last month comparison
    last_month_trans = Transaction.objects.filter(user=request.user, date__gte=last_month_start, date__lte=last_month_end)
    last_month_income = last_month_trans.filter(trans_type='income').aggregate(total=Sum('amount'))['total'] or 0
    last_month_expenses = last_month_trans.filter(trans_type='expense').aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate percentage changes
    income_change = ((income - last_month_income) / last_month_income * 100) if last_month_income else 0
    expense_change = ((expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses else 0
    
    # Account balances
    accounts = Account.objects.filter(user=request.user)
    total_balance = sum(float(acc.balance) for acc in accounts)
    
    # Recent transactions (last 5)
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Top spending categories
    cat_totals = {}
    for t in trans.filter(trans_type='expense'):
        splits = list(t.splits.all())
        if splits:
            for s in splits:
                name = s.category.name if s.category else 'Uncategorized'
                cat_totals[name] = cat_totals.get(name, 0) + float(s.amount)
        else:
            name = t.category.name if t.category else 'Uncategorized'
            cat_totals[name] = cat_totals.get(name, 0) + float(t.amount)
    
    by_category = sorted([{'category__name': k, 'total': v} for k, v in cat_totals.items()], key=lambda x: x['total'], reverse=True)[:6]
    
    # Budget analysis with alerts
    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    budget_alerts = []
    
    for b in budgets:
        spent = Transaction.objects.filter(
            user=request.user, 
            category=b.category, 
            trans_type='expense',
            date__gte=start_month, 
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pct = (spent / b.amount * 100) if b.amount and b.amount > 0 else 0
        remaining = float(b.amount) - float(spent)
        
        # Budget status and alerts
        status = 'success'
        if pct >= 90:
            status = 'danger'
            budget_alerts.append(f"Budget '{b.name}' is {pct:.1f}% used!")
        elif pct >= 75:
            status = 'warning'
            budget_alerts.append(f"Budget '{b.name}' is {pct:.1f}% used")
        elif pct >= 50:
            status = 'info'
            
        budget_data.append({
            'budget': b, 
            'spent': spent, 
            'remaining': remaining,
            'percent': round(pct, 2),
            'status': status
        })
    
    # Financial Health Score (0-100)
    health_score = calculate_financial_health_score(request.user, income, expenses, total_balance)
    
    # Weekly spending trend (last 4 weeks)
    four_weeks_ago = today - timedelta(weeks=4)
    weekly_qs = Transaction.objects.filter(
        user=request.user, 
        trans_type='expense',
        date__gte=four_weeks_ago, 
        date__lte=today
    ).annotate(week=TruncWeek('date')).values('week').annotate(total=Sum('amount')).order_by('week')
    
    weekly_totals = [{'week': d['week'].strftime('%Y-%m-%d'), 'total': float(d['total'] or 0)} for d in weekly_qs]
    
    # Daily spending for current month
    daily_qs = Transaction.objects.filter(
        user=request.user, 
        trans_type='expense',
        date__gte=start_month, 
        date__lte=today
    ).annotate(day=TruncDay('date')).values('day').annotate(total=Sum('amount')).order_by('day')
    
    daily_totals = [{'day': d['day'].strftime('%Y-%m-%d'), 'total': float(d['total'] or 0)} for d in daily_qs]
    
    # Spending insights
    insights = generate_spending_insights(request.user, trans, by_category, expenses, last_month_expenses)
    
    return render(request, 'dashboard.html', {
        'income': income,
        'expenses': expenses,
        'net': net,
        'income_change': round(income_change, 1),
        'expense_change': round(expense_change, 1),
        'total_balance': total_balance,
        'accounts': accounts,
        'recent_transactions': recent_transactions,
        'by_category': by_category,
        'budget_data': budget_data,
        'budget_alerts': budget_alerts,
        'health_score': health_score,
        'weekly_totals': weekly_totals,
        'daily_totals': daily_totals,
        'insights': insights,
    })


def calculate_financial_health_score(user, income, expenses, total_balance):
    """Calculate a financial health score from 0-100"""
    from decimal import Decimal
    score = 0
    
    # Convert total_balance to Decimal for consistent arithmetic
    total_balance = Decimal(str(total_balance))
    
    # Savings rate (40 points max)
    if income > 0:
        savings_rate = (income - expenses) / income
        if savings_rate >= Decimal('0.2'):  # 20% or more
            score += 40
        elif savings_rate >= Decimal('0.1'):  # 10-20%
            score += 30
        elif savings_rate >= Decimal('0.05'):  # 5-10%
            score += 20
        elif savings_rate > 0:  # Positive savings
            score += 10
    
    # Emergency fund (30 points max)
    monthly_expenses = expenses
    if monthly_expenses > 0 and total_balance > 0:
        months_covered = total_balance / monthly_expenses
        if months_covered >= Decimal('6'):  # 6+ months
            score += 30
        elif months_covered >= Decimal('3'):  # 3-6 months
            score += 20
        elif months_covered >= Decimal('1'):  # 1-3 months
            score += 10
    
    # Budget adherence (20 points max)
    budgets = Budget.objects.filter(user=user)
    if budgets.exists():
        over_budget_count = 0
        for budget in budgets:
            spent = Transaction.objects.filter(
                user=user, 
                category=budget.category, 
                trans_type='expense'
            ).aggregate(total=Sum('amount'))['total'] or 0
            if spent > budget.amount:
                over_budget_count += 1
        
        adherence_rate = 1 - (over_budget_count / budgets.count())
        score += adherence_rate * 20
    else:
        score += 10  # Bonus for having budgets set up
    
    # Transaction regularity (10 points max)
    recent_transactions = Transaction.objects.filter(user=user).count()
    if recent_transactions >= 10:
        score += 10
    elif recent_transactions >= 5:
        score += 5
    
    return min(100, max(0, round(score)))


def generate_spending_insights(user, transactions, by_category, current_expenses, last_month_expenses):
    """Generate personalized spending insights"""
    insights = []
    
    # Spending trend
    if last_month_expenses > 0:
        change = ((current_expenses - last_month_expenses) / last_month_expenses) * 100
        if change > 20:
            insights.append({
                'type': 'warning',
                'title': 'Spending Increase',
                'message': f'Your spending increased by {change:.1f}% compared to last month.'
            })
        elif change < -10:
            insights.append({
                'type': 'success',
                'title': 'Great Savings!',
                'message': f'You reduced spending by {abs(change):.1f}% compared to last month.'
            })
    
    # Top category insight
    if by_category:
        top_category = by_category[0]
        from decimal import Decimal
        percentage = float(Decimal(str(top_category['total'])) / current_expenses * 100) if current_expenses > 0 else 0
        if percentage > 40:
            insights.append({
                'type': 'info',
                'title': 'Top Spending Category',
                'message': f'{top_category["category__name"]} accounts for {percentage:.1f}% of your spending.'
            })
    
    # Transaction frequency
    transaction_count = transactions.count()
    if transaction_count > 50:
        insights.append({
            'type': 'info',
            'title': 'Active Spender',
            'message': f'You made {transaction_count} transactions this month. Consider consolidating purchases.'
        })
    
    return insights


@login_required
def budgets_list(request):
    qs = Budget.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'budgets_list.html', {'budgets': qs})


@login_required
def budget_create(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.user = request.user
            b.save()
            messages.success(request, 'Budget created.')
            return redirect('budgets')
    else:
        form = BudgetForm()
    return render(request, 'budget_form.html', {'form': form})


@login_required
def budget_edit(request, pk):
    b = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=b)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated.')
            return redirect('budgets')
    else:
        form = BudgetForm(instance=b)
    return render(request, 'budget_form.html', {'form': form, 'edit': True})


@login_required
def budget_delete(request, pk):
    b = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        b.delete()
        messages.success(request, 'Budget deleted.')
        return redirect('budgets')
    return render(request, 'transaction_confirm_delete.html', {'object': b})


@login_required
def recurring_list(request):
    qs = RecurringTransaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'recurring_list.html', {'recurrings': qs})


@login_required
def recurring_create(request):
    if request.method == 'POST':
        form = RecurringTransactionForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.user = request.user
            r.save()
            messages.success(request, 'Recurring transaction created.')
            return redirect('recurrings')
    else:
        form = RecurringTransactionForm()
    return render(request, 'recurring_form.html', {'form': form})


@login_required
def recurring_edit(request, pk):
    r = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = RecurringTransactionForm(request.POST, instance=r)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurring transaction updated.')
            return redirect('recurrings')
    else:
        form = RecurringTransactionForm(instance=r)
    return render(request, 'recurring_form.html', {'form': form, 'edit': True})


@login_required
def recurring_delete(request, pk):
    r = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    if request.method == 'POST':
        r.delete()
        messages.success(request, 'Recurring transaction deleted.')
        return redirect('recurrings')
    return render(request, 'transaction_confirm_delete.html', {'object': r})


@login_required
def split_create(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionSplitForm(request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.transaction = t
            s.save()
            messages.success(request, 'Split added.')
            return redirect('transaction_edit', pk=t.pk)
    else:
        form = TransactionSplitForm()
    return render(request, 'split_form.html', {'form': form, 'transaction': t})


@login_required
def split_edit(request, pk):
    s = get_object_or_404(TransactionSplit, pk=pk, transaction__user=request.user)
    if request.method == 'POST':
        form = TransactionSplitForm(request.POST, instance=s)
        if form.is_valid():
            form.save()
            messages.success(request, 'Split updated.')
            return redirect('transaction_edit', pk=s.transaction.pk)
    else:
        form = TransactionSplitForm(instance=s)
    return render(request, 'split_form.html', {'form': form, 'transaction': s.transaction, 'edit': True})


@login_required
def split_delete(request, pk):
    s = get_object_or_404(TransactionSplit, pk=pk, transaction__user=request.user)
    t = s.transaction
    if request.method == 'POST':
        s.delete()
        messages.success(request, 'Split deleted.')
        return redirect('transaction_edit', pk=t.pk)
    return render(request, 'transaction_confirm_delete.html', {'object': s})


# ============ PHASE 2: ADVANCED FEATURES ============

# Transaction Templates Views
@login_required
def templates_list(request):
    templates = TransactionTemplate.objects.filter(user=request.user).order_by('-use_count', 'name')
    return render(request, 'templates_list.html', {'templates': templates})


@login_required
def template_create(request):
    if request.method == 'POST':
        form = TransactionTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()
            messages.success(request, f'Template "{template.name}" created successfully.')
            return redirect('templates')
    else:
        form = TransactionTemplateForm()
    return render(request, 'template_form.html', {'form': form})


@login_required
def template_use(request, pk):
    template = get_object_or_404(TransactionTemplate, pk=pk, user=request.user)
    transaction = template.create_transaction()
    messages.success(request, f'Transaction created from template "{template.name}".')
    return redirect('transaction_edit', pk=transaction.pk)


@login_required
def template_delete(request, pk):
    template = get_object_or_404(TransactionTemplate, pk=pk, user=request.user)
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Template deleted.')
        return redirect('templates')
    return render(request, 'template_confirm_delete.html', {'object': template})


# Savings Goals Views
@login_required
def goals_list(request):
    goals = SavingsGoal.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'goals_list.html', {'goals': goals})


@login_required
def goal_create(request):
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Goal "{goal.name}" created successfully.')
            return redirect('goals')
    else:
        form = SavingsGoalForm()
    return render(request, 'goal_form.html', {'form': form})


@login_required
def goal_detail(request, pk):
    """View to display details of a specific savings goal."""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    
    # Get recent contributions for this goal (last 5)
    recent_contributions = GoalContribution.objects.filter(
        goal=goal
    ).order_by('-date_created')[:5]
    
    # Calculate days remaining if there's a target date
    days_remaining = None
    if goal.target_date:
        days_remaining = (goal.target_date - date.today()).days
        days_remaining = max(0, days_remaining)  # Don't show negative days
    
    # Calculate suggested contribution
    suggested_contribution = None
    if goal.target_date and goal.target_amount > goal.current_amount and days_remaining > 0:
        remaining_amount = goal.target_amount - goal.current_amount
        suggested_contribution = remaining_amount / days_remaining
    
    context = {
        'goal': goal,
        'recent_contributions': recent_contributions,
        'days_remaining': days_remaining,
        'suggested_contribution': suggested_contribution,
    }
    
    return render(request, 'goal_detail.html', context)
def goal_contribute(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    remaining_balance = goal.target_amount - goal.current_amount
    
    if request.method == 'POST':
        form = GoalContributionForm(request.POST)
        if form.is_valid():
            contribution = form.save(commit=False)
            contribution_amount = contribution.amount
            
            # Check if contribution exceeds remaining balance
            if contribution_amount > remaining_balance:
                messages.error(
                    request, 
                    f"Contribution amount (KSh {contribution_amount:,.2f}) exceeds the remaining balance needed (KSh {remaining_balance:,.2f})."
                )
                return render(request, 'goal_contribute.html', {
                    'form': form, 
                    'goal': goal,
                    'remaining_balance': remaining_balance
                })
            
            contribution.goal = goal
            contribution.save()
            
            # Update goal amount
            goal.add_contribution(contribution.amount)
            
            if goal.status == 'completed':
                messages.success(request, f'Congratulations! You\'ve completed your goal "{goal.name}"!')
            else:
                messages.success(request, f'Added ${contribution.amount} to "{goal.name}". ${goal.remaining_amount:.2f} remaining.')
            
            return redirect('goals')
    else:
        form = GoalContributionForm()
    
    return render(request, 'goal_contribute.html', {
        'form': form, 
        'goal': goal,
        'remaining_balance': remaining_balance
    })


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Goal deleted.')
        return redirect('goals')
    return render(request, 'goal_confirm_delete.html', {'object': goal})


# Bills & Reminders Views
@login_required
def bills_list(request):
    from django.utils import timezone
    
    bills = Bill.objects.filter(user=request.user).order_by('due_date')
    
    # Update overdue status
    for bill in bills:
        if bill.is_overdue and bill.status == 'pending':
            bill.status = 'overdue'
            bill.save()
    
    # Separate bills by status
    upcoming_bills = bills.filter(status='pending', due_date__gte=timezone.now().date())
    overdue_bills = bills.filter(status='overdue')
    paid_bills = bills.filter(status='paid').order_by('-due_date')[:10]  # Last 10 paid bills
    
    return render(request, 'bills_list.html', {
        'upcoming_bills': upcoming_bills,
        'overdue_bills': overdue_bills,
        'paid_bills': paid_bills
    })


@login_required
def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.user = request.user
            bill.save()
            messages.success(request, f'Bill "{bill.name}" created successfully.')
            return redirect('bills')
    else:
        form = BillForm()
    return render(request, 'tracker/bill_form.html', {'form': form})


@login_required
def bill_pay(request, pk):
    bill = get_object_or_404(Bill, pk=pk, user=request.user)
    if request.method == 'POST':
        bill.mark_as_paid()
        messages.success(request, f'Bill "{bill.name}" marked as paid and transaction created.')
        return redirect('bills')
    return render(request, 'bill_pay_confirm.html', {'bill': bill})


@login_required
def bill_delete(request, pk):
    bill = get_object_or_404(Bill, pk=pk, user=request.user)
    if request.method == 'POST':
        bill.delete()
        messages.success(request, 'Bill deleted.')
        return redirect('bills')
    return render(request, 'tracker/bill_confirm_delete.html', {'object': bill})


# Advanced Transaction Management
@login_required
def transactions_advanced(request):
    from .forms import AdvancedSearchForm, BulkTransactionForm
    
    search_form = AdvancedSearchForm(request.GET or None, user=request.user)
    bulk_form = BulkTransactionForm(user=request.user)
    
    # Start with all user transactions
    qs = Transaction.objects.filter(user=request.user).order_by('-date', '-time')
    
    # Apply search filters
    if search_form.is_valid():
        if search_form.cleaned_data['query']:
            qs = qs.filter(description__icontains=search_form.cleaned_data['query'])
        if search_form.cleaned_data['category']:
            qs = qs.filter(category=search_form.cleaned_data['category'])
        if search_form.cleaned_data['trans_type']:
            qs = qs.filter(trans_type=search_form.cleaned_data['trans_type'])
        if search_form.cleaned_data['account']:
            qs = qs.filter(account=search_form.cleaned_data['account'])
        if search_form.cleaned_data['date_from']:
            qs = qs.filter(date__gte=search_form.cleaned_data['date_from'])
        if search_form.cleaned_data['date_to']:
            qs = qs.filter(date__lte=search_form.cleaned_data['date_to'])
        if search_form.cleaned_data['amount_min']:
            qs = qs.filter(amount__gte=search_form.cleaned_data['amount_min'])
        if search_form.cleaned_data['amount_max']:
            qs = qs.filter(amount__lte=search_form.cleaned_data['amount_max'])
        if search_form.cleaned_data['tags']:
            qs = qs.filter(tags__icontains=search_form.cleaned_data['tags'])
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 25)  # 25 transactions per page
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    return render(request, 'transactions_advanced.html', {
        'transactions': transactions,
        'search_form': search_form,
        'bulk_form': bulk_form,
        'total_count': qs.count()
    })


@login_required
def transactions_bulk_action(request):
    from .forms import BulkTransactionForm
    import csv
    from django.http import HttpResponse
    
    if request.method == 'POST':
        form = BulkTransactionForm(request.POST, user=request.user)
        selected_ids = request.POST.getlist('selected_transactions')
        
        if not selected_ids:
            messages.error(request, 'No transactions selected.')
            return redirect('transactions_advanced')
        
        transactions = Transaction.objects.filter(id__in=selected_ids, user=request.user)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'delete':
                count = transactions.count()
                transactions.delete()
                messages.success(request, f'Deleted {count} transactions.')
                
            elif action == 'change_category':
                category = form.cleaned_data['category']
                if category:
                    count = transactions.update(category=category)
                    messages.success(request, f'Updated category for {count} transactions.')
                else:
                    messages.error(request, 'Please select a category.')
                    
            elif action == 'add_tags':
                tags = form.cleaned_data['tags']
                if tags:
                    for transaction in transactions:
                        existing_tags = transaction.tags.split(',') if transaction.tags else []
                        new_tags = [tag.strip() for tag in tags.split(',')]
                        all_tags = list(set(existing_tags + new_tags))
                        transaction.tags = ','.join(filter(None, all_tags))
                        transaction.save()
                    messages.success(request, f'Added tags to {transactions.count()} transactions.')
                else:
                    messages.error(request, 'Please enter tags to add.')
                    
            elif action == 'export':
                # Export selected transactions to CSV
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="selected_transactions.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['Date', 'Type', 'Amount', 'Category', 'Account', 'Description', 'Tags'])
                
                for t in transactions:
                    writer.writerow([
                        t.date,
                        t.get_trans_type_display(),
                        t.amount,
                        t.category.name if t.category else '',
                        t.account.name if t.account else '',
                        t.description,
                        t.tags
                    ])
                
                return response
    
    return redirect('transactions_advanced')


# Enhanced Dashboard and Analytics Views

@login_required
def dashboard_enhanced(request):
    """Enhanced dashboard with charts and advanced analytics"""
    from django.db.models import Q, Count
    from datetime import datetime, timedelta
    import json
    
    today = timezone.now().date()
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    # Basic statistics
    current_month_income = Transaction.objects.filter(
        user=request.user, trans_type='income', date__gte=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    current_month_expenses = Transaction.objects.filter(
        user=request.user, trans_type='expense', date__gte=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    last_month_income = Transaction.objects.filter(
        user=request.user, trans_type='income', 
        date__gte=last_month, date__lt=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    last_month_expenses = Transaction.objects.filter(
        user=request.user, trans_type='expense',
        date__gte=last_month, date__lt=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate percentage changes
    income_change = ((current_month_income - last_month_income) / last_month_income * 100) if last_month_income else 0
    expense_change = ((current_month_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses else 0
    
    # Account balances
    total_balance = Account.objects.filter(user=request.user).aggregate(
        Sum('balance'))['balance__sum'] or 0
    
    # Category breakdown for pie chart
    category_data_raw = Transaction.objects.filter(
        user=request.user, trans_type='expense', date__gte=current_month
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]
    
    # Convert Decimal values to float for JSON serialization
    category_data = []
    for item in category_data_raw:
        category_data.append({
            'category__name': item['category__name'],
            'total': float(item['total']) if item['total'] else 0.0
        })
    
    # Daily spending trend for line chart (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    daily_spending = []
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        spending = Transaction.objects.filter(
            user=request.user, trans_type='expense', date=day
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        daily_spending.append({
            'date': day.strftime('%Y-%m-%d'),
            'amount': float(spending)
        })
    
    # Budget progress
    budgets = Budget.objects.filter(user=request.user)
    budget_progress = []
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=request.user,
            category=budget.category,
            trans_type='expense',
            date__gte=budget.start_date or current_month
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        progress_percent = (spent / budget.amount * 100) if budget.amount else 0
        budget_progress.append({
            'name': budget.name,
            'spent': float(spent),
            'budget': float(budget.amount),
            'progress': min(100, progress_percent),
            'status': 'danger' if progress_percent > 90 else 'warning' if progress_percent > 75 else 'success'
        })
    
    # Financial health score
    from .models import FinancialHealthScore, Notification
    health_score, created = FinancialHealthScore.objects.get_or_create(user=request.user)
    if created or (timezone.now() - health_score.last_calculated).days >= 1:
        health_score.calculate_score()
    
    # Recent notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
    
    # Savings goals progress
    goals = SavingsGoal.objects.filter(user=request.user, status='active')
    
    context = {
        'current_month_income': current_month_income,
        'current_month_expenses': current_month_expenses,
        'net_savings': current_month_income - current_month_expenses,
        'total_balance': total_balance,
        'income_change': income_change,
        'expense_change': expense_change,
        'category_data': json.dumps(category_data),
        'daily_spending': json.dumps(daily_spending),
        'budget_progress': budget_progress,
        'health_score': health_score,
        'notifications': notifications,
        'goals': goals,
    }
    
    return render(request, 'dashboard_enhanced.html', context)


@login_required
def notifications_view(request):
    """View and manage notifications"""
    from .models import Notification
    notifications = Notification.objects.filter(user=request.user)
    
    # Mark as read if requested
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
                messages.success(request, 'Notification marked as read.')
            except Notification.DoesNotExist:
                messages.error(request, 'Notification not found.')
        
        # Mark all as read
        elif request.POST.get('mark_all_read'):
            notifications.update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
    
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
def financial_health_view(request):
    """Detailed financial health analysis"""
    from .models import FinancialHealthScore
    health_score, created = FinancialHealthScore.objects.get_or_create(user=request.user)
    
    # Recalculate if requested or if outdated
    if request.GET.get('recalculate') or created or (timezone.now() - health_score.last_calculated).days >= 1:
        health_score.calculate_score()
    
    # Get improvement suggestions
    suggestions = []
    
    if health_score.savings_rate < 10:
        suggestions.append({
            'title': 'Increase Savings Rate',
            'description': 'Try to save at least 10-20% of your income each month.',
            'priority': 'high'
        })
    
    if health_score.emergency_fund_months < 3:
        suggestions.append({
            'title': 'Build Emergency Fund',
            'description': 'Aim for 3-6 months of expenses in your emergency fund.',
            'priority': 'high'
        })
    
    if health_score.budget_adherence < 75:
        suggestions.append({
            'title': 'Improve Budget Adherence',
            'description': 'Try to stick to your budgets more closely to improve financial discipline.',
            'priority': 'medium'
        })
    
    # Account diversity check
    account_count = Account.objects.filter(user=request.user).count()
    if account_count < 2:
        suggestions.append({
            'title': 'Diversify Accounts',
            'description': 'Consider having multiple accounts (checking, savings, investment) for better financial management.',
            'priority': 'low'
        })
    
    # Goals check
    active_goals = SavingsGoal.objects.filter(user=request.user, status='active').count()
    if active_goals == 0:
        suggestions.append({
            'title': 'Set Savings Goals',
            'description': 'Create specific savings goals to stay motivated and track progress.',
            'priority': 'medium'
        })
    
    context = {
        'health_score': health_score,
        'suggestions': suggestions,
        'account_count': account_count,
        'active_goals': active_goals,
    }
    
    return render(request, 'financial_health.html', context)


@login_required
def generate_pdf_report_view(request):
    """Generate and download PDF reports"""
    from .utils.reports import generate_pdf_report
    from datetime import datetime
    
    # Get parameters
    report_type = request.GET.get('type', 'monthly')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Parse dates if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
    
    try:
        return generate_pdf_report(request.user, report_type, start_date, end_date)
    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('dashboard_enhanced')


@login_required
def advanced_search_view(request):
    """Advanced search with autocomplete and filters"""
    from django.db.models import Q
    from django.http import JsonResponse
    import json
    
    # Handle AJAX requests for autocomplete
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        search_type = request.GET.get('type', 'description')
        
        if search_type == 'description':
            # Get unique descriptions that match the query
            suggestions = Transaction.objects.filter(
                user=request.user,
                description__icontains=query
            ).values_list('description', flat=True).distinct()[:10]
        
        elif search_type == 'category':
            # Get categories that match the query
            suggestions = Category.objects.filter(
                name__icontains=query
            ).values_list('name', flat=True)[:10]
        
        elif search_type == 'account':
            # Get user's accounts that match the query
            suggestions = Account.objects.filter(
                user=request.user,
                name__icontains=query
            ).values_list('name', flat=True)[:10]
        
        elif search_type == 'tags':
            # Get unique tags that match the query
            all_tags = Transaction.objects.filter(
                user=request.user,
                tags__icontains=query
            ).values_list('tags', flat=True)
            
            # Parse tags and find matches
            suggestions = set()
            for tag_string in all_tags:
                if tag_string:
                    tags = [tag.strip() for tag in tag_string.split(',')]
                    for tag in tags:
                        if query.lower() in tag.lower():
                            suggestions.add(tag)
            suggestions = list(suggestions)[:10]
        
        else:
            suggestions = []
        
        return JsonResponse({'suggestions': list(suggestions)})
    
    # Handle search form submission
    transactions = Transaction.objects.filter(user=request.user)
    
    # Get search parameters
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    account_id = request.GET.get('account')
    trans_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    amount_min = request.GET.get('amount_min')
    amount_max = request.GET.get('amount_max')
    tags = request.GET.get('tags', '')
    sort_by = request.GET.get('sort', '-date')
    
    # Apply filters
    if query:
        transactions = transactions.filter(
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(account__name__icontains=query) |
            Q(tags__icontains=query)
        )
    
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    if account_id:
        transactions = transactions.filter(account_id=account_id)
    
    if trans_type:
        transactions = transactions.filter(trans_type=trans_type)
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    if amount_min:
        try:
            transactions = transactions.filter(amount__gte=float(amount_min))
        except ValueError:
            pass
    
    if amount_max:
        try:
            transactions = transactions.filter(amount__lte=float(amount_max))
        except ValueError:
            pass
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        for tag in tag_list:
            if tag:
                transactions = transactions.filter(tags__icontains=tag)
    
    # Apply sorting
    valid_sorts = ['-date', 'date', '-amount', 'amount', '-created_at', 'created_at']
    if sort_by in valid_sorts:
        transactions = transactions.order_by(sort_by)
    else:
        transactions = transactions.order_by('-date', '-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Save search for recent searches
    if query or any([category_id, account_id, trans_type, date_from, date_to, amount_min, amount_max, tags]):
        search_data = {
            'query': query,
            'category_id': category_id,
            'account_id': account_id,
            'trans_type': trans_type,
            'date_from': date_from,
            'date_to': date_to,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'tags': tags,
            'timestamp': timezone.now().isoformat()
        }
        
        # Store in session (in production, you might want to store in database)
        recent_searches = request.session.get('recent_searches', [])
        recent_searches.insert(0, search_data)
        request.session['recent_searches'] = recent_searches[:10]  # Keep last 10 searches
    
    context = {
        'transactions': page_obj,
        'categories': Category.objects.all(),
        'accounts': Account.objects.filter(user=request.user),
        'search_params': {
            'q': query,
            'category': category_id,
            'account': account_id,
            'type': trans_type,
            'date_from': date_from,
            'date_to': date_to,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'tags': tags,
            'sort': sort_by,
        },
        'recent_searches': request.session.get('recent_searches', [])[:5],
        'total_results': paginator.count,
    }
    
    return render(request, 'advanced_search.html', context)


@login_required
def calendar_view(request):
    """Calendar view of transactions"""
    from datetime import datetime, timedelta
    import calendar
    import json
    
    # Get current month/year or from parameters
    try:
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
    except (ValueError, TypeError):
        year = timezone.now().year
        month = timezone.now().month
    
    # Ensure valid month/year
    if month < 1 or month > 12:
        month = timezone.now().month
    if year < 2000 or year > 2100:
        year = timezone.now().year
    
    # Get first and last day of the month
    first_day = datetime(year, month, 1).date()
    if month == 12:
        last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Get transactions for the month
    transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=first_day,
        date__lte=last_day
    ).select_related('category', 'account').order_by('date', 'created_at')
    
    # Group transactions by date
    transactions_by_date = {}
    daily_totals = {}
    
    for transaction in transactions:
        date_str = transaction.date.strftime('%Y-%m-%d')
        if date_str not in transactions_by_date:
            transactions_by_date[date_str] = []
            daily_totals[date_str] = {'income': 0, 'expense': 0, 'net': 0}
        
        transactions_by_date[date_str].append({
            'id': transaction.id,
            'amount': float(transaction.amount),
            'type': transaction.trans_type,
            'category': transaction.category.name if transaction.category else 'Uncategorized',
            'account': transaction.account.name if transaction.account else 'N/A',
            'description': transaction.description,
            'time': transaction.time.strftime('%H:%M') if transaction.time else '',
        })
        
        if transaction.trans_type == 'income':
            daily_totals[date_str]['income'] += float(transaction.amount)
        elif transaction.trans_type == 'expense':
            daily_totals[date_str]['expense'] += float(transaction.amount)
        
        daily_totals[date_str]['net'] = daily_totals[date_str]['income'] - daily_totals[date_str]['expense']
    
    # Generate calendar data
    cal = calendar.Calendar(firstweekday=6)  # Start with Sunday
    month_days = cal.monthdayscalendar(year, month)
    
    # Calculate navigation dates
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # Monthly summary
    monthly_income = sum(total['income'] for total in daily_totals.values())
    monthly_expenses = sum(total['expense'] for total in daily_totals.values())
    monthly_net = monthly_income - monthly_expenses
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'month_days': month_days,
        'transactions_by_date': json.dumps(transactions_by_date),
        'daily_totals': json.dumps(daily_totals),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'monthly_net': monthly_net,
        'weekdays': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    }
    
    return render(request, 'calendar_view.html', context)


@login_required
def ai_insights_view(request):
    """AI-powered financial insights and predictions"""
    from django.db.models import Avg, Count
    from datetime import datetime, timedelta
    import json
    
    today = timezone.now().date()
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    three_months_ago = (current_month - timedelta(days=90)).replace(day=1)
    
    # Get user's transaction data for analysis
    recent_transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=three_months_ago
    ).select_related('category', 'account')
    
    # Generate AI insights
    insights = generate_ai_insights(request.user, recent_transactions)
    
    # Spending predictions
    predictions = generate_spending_predictions(request.user, recent_transactions)
    
    # Category analysis
    category_insights = analyze_spending_categories(request.user, recent_transactions)
    
    # Savings opportunities
    savings_opportunities = find_savings_opportunities(request.user, recent_transactions)
    
    context = {
        'insights': insights,
        'predictions': predictions,
        'category_insights': category_insights,
        'savings_opportunities': savings_opportunities,
    }
    
    return render(request, 'ai_insights.html', context)


def generate_ai_insights(user, transactions):
    """Generate AI-powered financial insights"""
    from django.db.models import Sum, Avg, Count
    from datetime import timedelta
    
    insights = []
    today = timezone.now().date()
    
    # Spending trend analysis
    current_month_spending = transactions.filter(
        trans_type='expense',
        date__gte=today.replace(day=1)
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    last_month_spending = transactions.filter(
        trans_type='expense',
        date__gte=(today.replace(day=1) - timedelta(days=30)).replace(day=1),
        date__lt=today.replace(day=1)
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    if float(last_month_spending) > 0:
        spending_change = ((float(current_month_spending) - float(last_month_spending)) / float(last_month_spending)) * 100
        if spending_change > 20:
            insights.append({
                'type': 'warning',
                'title': 'Increased Spending Detected',
                'description': f'Your spending has increased by {spending_change:.1f}% this month. Consider reviewing your recent purchases.',
                'action': 'Review recent transactions',
                'priority': 'high'
            })
        elif spending_change < -10:
            insights.append({
                'type': 'success',
                'title': 'Great Spending Control',
                'description': f'You\'ve reduced spending by {abs(spending_change):.1f}% this month. Keep up the good work!',
                'action': 'Maintain current habits',
                'priority': 'low'
            })
    
    # Frequent transaction analysis
    frequent_merchants = transactions.filter(
        trans_type='expense'
    ).values('description').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).filter(count__gte=3).order_by('-total')[:3]
    
    for merchant in frequent_merchants:
        if float(merchant['total']) > 200:  # Significant spending
            insights.append({
                'type': 'info',
                'title': f'Frequent Spending: {merchant["description"]}',
                'description': f'You\'ve spent ${merchant["total"]:.2f} across {merchant["count"]} transactions here.',
                'action': 'Consider if this aligns with your budget',
                'priority': 'medium'
            })
    
    # Weekend vs weekday spending
    weekend_spending = transactions.filter(
        trans_type='expense',
        date__week_day__in=[1, 7]  # Sunday=1, Saturday=7
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    weekday_spending = transactions.filter(
        trans_type='expense',
        date__week_day__in=[2, 3, 4, 5, 6]  # Monday-Friday
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    if float(weekend_spending) > float(weekday_spending) * 0.4:  # Weekend spending > 40% of weekday
        insights.append({
            'type': 'info',
            'title': 'Weekend Spending Pattern',
            'description': 'You tend to spend more on weekends. Consider planning weekend activities within budget.',
            'action': 'Set weekend spending limits',
            'priority': 'medium'
        })
    
    # Income vs expense ratio
    total_income = transactions.filter(trans_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = transactions.filter(trans_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    
    if float(total_income) > 0:
        savings_rate = ((float(total_income) - float(total_expenses)) / float(total_income)) * 100
        if savings_rate < 10:
            insights.append({
                'type': 'warning',
                'title': 'Low Savings Rate',
                'description': f'Your savings rate is {savings_rate:.1f}%. Financial experts recommend saving at least 20%.',
                'action': 'Identify areas to reduce spending',
                'priority': 'high'
            })
        elif savings_rate > 30:
            insights.append({
                'type': 'success',
                'title': 'Excellent Savings Rate',
                'description': f'Your savings rate of {savings_rate:.1f}% is outstanding! Consider investing surplus funds.',
                'action': 'Explore investment opportunities',
                'priority': 'low'
            })
    
    return insights


def generate_spending_predictions(user, transactions):
    """Generate spending predictions based on historical data"""
    from django.db.models import Sum
    from datetime import timedelta
    import statistics
    
    today = timezone.now().date()
    predictions = []
    
    # Monthly spending prediction
    monthly_expenses = []
    for i in range(3):  # Last 3 months
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start.replace(month=month_start.month+1) - timedelta(days=1)) if month_start.month < 12 else month_start.replace(year=month_start.year+1, month=1) - timedelta(days=1)
        
        month_spending = transactions.filter(
            trans_type='expense',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_expenses.append(float(month_spending))
    
    if len(monthly_expenses) >= 2:
        avg_monthly = statistics.mean(monthly_expenses)
        trend = (monthly_expenses[0] - monthly_expenses[-1]) / len(monthly_expenses)
        next_month_prediction = avg_monthly + trend
        
        predictions.append({
            'type': 'monthly_spending',
            'title': 'Next Month Spending Prediction',
            'predicted_amount': next_month_prediction,
            'confidence': 75,
            'description': f'Based on your recent patterns, you\'ll likely spend ${next_month_prediction:.2f} next month.',
            'trend': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable'
        })
    
    # Category-based predictions
    top_categories = transactions.filter(
        trans_type='expense'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:3]
    
    for category in top_categories:
        if category['category__name']:
            category_transactions = transactions.filter(
                trans_type='expense',
                category__name=category['category__name']
            )
            
            monthly_avg = category_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
            monthly_avg = monthly_avg / 3  # Average over 3 months
            
            predictions.append({
                'type': 'category_spending',
                'title': f'{category["category__name"]} Spending',
                'predicted_amount': monthly_avg,
                'confidence': 65,
                'description': f'Expected to spend ${monthly_avg:.2f} on {category["category__name"]} next month.',
                'category': category['category__name']
            })
    
    return predictions


def analyze_spending_categories(user, transactions):
    """Analyze spending patterns by category"""
    from django.db.models import Sum, Count, Avg
    
    category_analysis = transactions.filter(
        trans_type='expense'
    ).values('category__name').annotate(
        total_spent=Sum('amount'),
        transaction_count=Count('id'),
        avg_transaction=Avg('amount')
    ).order_by('-total_spent')
    
    insights = []
    total_spending = sum(float(cat['total_spent']) for cat in category_analysis)
    
    for category in category_analysis[:5]:  # Top 5 categories
        percentage = (float(category['total_spent']) / total_spending * 100) if total_spending > 0 else 0
        
        insight = {
            'category': category['category__name'] or 'Uncategorized',
            'total_spent': float(category['total_spent']),
            'percentage': percentage,
            'transaction_count': category['transaction_count'],
            'avg_transaction': float(category['avg_transaction']),
            'recommendation': ''
        }
        
        # Generate recommendations
        if percentage > 40:
            insight['recommendation'] = 'This category dominates your spending. Consider if this aligns with your priorities.'
        elif percentage > 25:
            insight['recommendation'] = 'Significant spending category. Monitor for optimization opportunities.'
        elif category['avg_transaction'] > 100:
            insight['recommendation'] = 'High average transaction amount. Consider if these purchases are necessary.'
        else:
            insight['recommendation'] = 'Well-controlled spending in this category.'
        
        insights.append(insight)
    
    return insights


def find_savings_opportunities(user, transactions):
    """Identify potential savings opportunities"""
    from django.db.models import Sum, Count
    from collections import Counter
    
    opportunities = []
    
    # Subscription-like recurring expenses
    recurring_expenses = transactions.filter(
        trans_type='expense'
    ).values('description', 'amount').annotate(
        count=Count('id')
    ).filter(count__gte=2, amount__gte=10).order_by('-amount')
    
    for expense in recurring_expenses[:3]:
        annual_cost = float(expense['amount']) * 12
        if annual_cost > 200:
            opportunities.append({
                'type': 'subscription_review',
                'title': f'Review: {expense["description"]}',
                'potential_savings': annual_cost * 0.3,  # Assume 30% potential savings
                'description': f'This recurring expense costs ${annual_cost:.2f} annually. Consider if it\'s still needed.',
                'action': 'Review and potentially cancel or downgrade',
                'priority': 'medium'
            })
    
    # High-frequency small purchases
    small_frequent = transactions.filter(
        trans_type='expense',
        amount__lt=20,
        amount__gt=5
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).filter(count__gte=10).order_by('-total')
    
    for category in small_frequent[:2]:
        if category['category__name']:
            opportunities.append({
                'type': 'small_purchases',
                'title': f'Small Purchases: {category["category__name"]}',
                'potential_savings': float(category['total']) * 0.25,
                'description': f'${category["total"]:.2f} spent on {category["count"]} small purchases. Consider bulk buying or alternatives.',
                'action': 'Plan purchases or find alternatives',
                'priority': 'low'
            })
    
    # Weekend spending optimization
    weekend_expenses = transactions.filter(
        trans_type='expense',
        date__week_day__in=[1, 7]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    if float(weekend_expenses) > 500:
        opportunities.append({
            'type': 'weekend_spending',
            'title': 'Weekend Spending Optimization',
            'potential_savings': float(weekend_expenses) * 0.2,
            'description': f'${weekend_expenses:.2f} spent on weekends. Plan free or low-cost weekend activities.',
            'action': 'Plan budget-friendly weekend activities',
            'priority': 'medium'
        })
    
    return opportunities


@login_required
def voice_transaction_view(request):
    """Voice input for transactions"""
    from django.http import JsonResponse
    import re
    from decimal import Decimal, InvalidOperation
    
    if request.method == 'POST':
        voice_text = request.POST.get('voice_text', '').lower().strip()
        
        if not voice_text:
            return JsonResponse({'error': 'No voice input provided'})
        
        # Parse voice input using simple patterns
        parsed_data = parse_voice_input(voice_text)
        
        if parsed_data.get('error'):
            return JsonResponse({'error': parsed_data['error']})
        
        # Try to create transaction from parsed data
        try:
            # Get or create category
            category = None
            if parsed_data.get('category'):
                category, _ = Category.objects.get_or_create(
                    name__iexact=parsed_data['category'],
                    defaults={'name': parsed_data['category'].title()}
                )
            
            # Get user's default account or first account
            account = Account.objects.filter(user=request.user).first()
            
            # Create transaction
            transaction = Transaction.objects.create(
                user=request.user,
                amount=parsed_data['amount'],
                trans_type=parsed_data['type'],
                category=category,
                account=account,
                description=parsed_data.get('description', ''),
                date=parsed_data.get('date', timezone.now().date())
            )
            
            return JsonResponse({
                'success': True,
                'transaction': {
                    'id': transaction.id,
                    'amount': float(transaction.amount),
                    'type': transaction.trans_type,
                    'category': transaction.category.name if transaction.category else None,
                    'description': transaction.description,
                    'date': transaction.date.strftime('%Y-%m-%d')
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to create transaction: {str(e)}'})
    
    # GET request - show voice input page
    return render(request, 'voice_transaction.html')


def parse_voice_input(text):
    """Parse voice input text to extract transaction data"""
    import re
    from decimal import Decimal, InvalidOperation
    
    # Common patterns for voice input
    patterns = {
        'spent': r'(?:spent|spend|paid|pay)\s+(?:\$)?(\d+(?:\.\d{2})?)',
        'earned': r'(?:earned|earn|received|receive|got|income)\s+(?:\$)?(\d+(?:\.\d{2})?)',
        'transferred': r'(?:transferred|transfer|moved|move)\s+(?:\$)?(\d+(?:\.\d{2})?)',
    }
    
    # Extract amount and type
    amount = None
    trans_type = 'expense'  # default
    
    for pattern_type, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = Decimal(match.group(1))
                if pattern_type == 'earned':
                    trans_type = 'income'
                elif pattern_type == 'transferred':
                    trans_type = 'transfer'
                else:
                    trans_type = 'expense'
                break
            except InvalidOperation:
                continue
    
    # If no pattern matched, try to extract just a number
    if amount is None:
        amount_match = re.search(r'(?:\$)?(\d+(?:\.\d{2})?)', text)
        if amount_match:
            try:
                amount = Decimal(amount_match.group(1))
            except InvalidOperation:
                return {'error': 'Could not parse amount from voice input'}
        else:
            return {'error': 'No amount found in voice input'}
    
    # Extract category keywords
    category_keywords = {
        'food': ['food', 'restaurant', 'lunch', 'dinner', 'breakfast', 'coffee', 'groceries', 'grocery'],
        'transportation': ['gas', 'fuel', 'uber', 'taxi', 'bus', 'train', 'parking'],
        'shopping': ['shopping', 'clothes', 'amazon', 'store', 'bought'],
        'entertainment': ['movie', 'movies', 'game', 'games', 'entertainment', 'fun'],
        'bills': ['bill', 'bills', 'utility', 'utilities', 'rent', 'insurance'],
        'healthcare': ['doctor', 'medicine', 'pharmacy', 'hospital', 'health'],
        'salary': ['salary', 'paycheck', 'work', 'job'],
        'freelance': ['freelance', 'client', 'project', 'consulting'],
    }
    
    category = None
    for cat_name, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                category = cat_name.title()
                break
        if category:
            break
    
    # Extract description (remove amount and common words)
    description = text
    # Remove amount mentions
    description = re.sub(r'(?:\$)?\d+(?:\.\d{2})?', '', description)
    # Remove common transaction words
    common_words = ['spent', 'spend', 'paid', 'pay', 'earned', 'earn', 'received', 'receive', 'got', 'on', 'for', 'at']
    for word in common_words:
        description = re.sub(r'\b' + word + r'\b', '', description, flags=re.IGNORECASE)
    
    description = ' '.join(description.split()).strip()
    
    return {
        'amount': amount,
        'type': trans_type,
        'category': category,
        'description': description or 'Voice transaction',
        'date': timezone.now().date()
    }
