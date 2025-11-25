from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    Transaction, Budget, Bill, SavingsGoal, FinancialHealthScore, 
    Notification, BudgetAlert, UserPreferences
)


@shared_task
def calculate_financial_health_scores():
    """Calculate financial health scores for all users"""
    users = User.objects.all()
    for user in users:
        health_score, created = FinancialHealthScore.objects.get_or_create(user=user)
        health_score.calculate_score()
    return f"Updated financial health scores for {users.count()} users"


@shared_task
def check_budget_alerts():
    """Check for budget threshold alerts and create notifications"""
    budgets = Budget.objects.filter(
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    )
    
    alerts_created = 0
    for budget in budgets:
        # Calculate spent amount for this budget period
        spent = Transaction.objects.filter(
            user=budget.user,
            category=budget.category,
            trans_type='expense',
            date__gte=budget.start_date or timezone.now().date().replace(day=1),
            date__lte=budget.end_date or timezone.now().date()
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        if budget.amount > 0:
            percentage_used = (spent / budget.amount) * 100
            
            # Check thresholds and create alerts
            alert_types = []
            if percentage_used >= 100:
                alert_types.append('100_percent')
            elif percentage_used >= 90:
                alert_types.append('90_percent')
            elif percentage_used >= 75:
                alert_types.append('75_percent')
            elif percentage_used >= 50:
                alert_types.append('50_percent')
            
            for alert_type in alert_types:
                alert, created = BudgetAlert.objects.get_or_create(
                    budget=budget,
                    alert_type=alert_type
                )
                
                if created and not alert.is_sent:
                    # Create notification
                    title = f"Budget Alert: {budget.name}"
                    message = f"You've used {percentage_used:.1f}% of your {budget.name} budget (${spent} of ${budget.amount})"
                    
                    Notification.objects.create(
                        user=budget.user,
                        title=title,
                        message=message,
                        notification_type='budget_alert',
                        priority='high' if percentage_used >= 90 else 'medium'
                    )
                    
                    # Send email if user has email notifications enabled
                    preferences = getattr(budget.user, 'userpreferences', None)
                    if preferences and preferences.budget_alerts and preferences.email_notifications:
                        send_budget_alert_email.delay(budget.user.id, title, message)
                    
                    alert.is_sent = True
                    alert.save()
                    alerts_created += 1
    
    return f"Created {alerts_created} budget alerts"


@shared_task
def send_budget_alert_email(user_id, title, message):
    """Send budget alert email to user"""
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            subject=title,
            message=message,
            from_email='noreply@expensetracker.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
        return f"Budget alert email sent to {user.email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@shared_task
def check_bill_reminders():
    """Check for upcoming bills and send reminders"""
    today = timezone.now().date()
    upcoming_bills = Bill.objects.filter(
        status='pending',
        due_date__lte=today + timedelta(days=7)
    )
    
    reminders_sent = 0
    for bill in upcoming_bills:
        days_until_due = (bill.due_date - today).days
        
        # Send reminder based on user's reminder preference
        if days_until_due <= bill.reminder_days:
            title = f"Bill Reminder: {bill.name}"
            if days_until_due == 0:
                message = f"Your bill '{bill.name}' for ${bill.amount} is due today!"
                priority = 'urgent'
            elif days_until_due < 0:
                message = f"Your bill '{bill.name}' for ${bill.amount} is {abs(days_until_due)} days overdue!"
                priority = 'urgent'
                bill.status = 'overdue'
                bill.save()
            else:
                message = f"Your bill '{bill.name}' for ${bill.amount} is due in {days_until_due} days."
                priority = 'medium'
            
            # Check if reminder already sent today
            existing_notification = Notification.objects.filter(
                user=bill.user,
                notification_type='bill_reminder',
                title=title,
                created_at__date=today
            ).exists()
            
            if not existing_notification:
                Notification.objects.create(
                    user=bill.user,
                    title=title,
                    message=message,
                    notification_type='bill_reminder',
                    priority=priority
                )
                
                # Send email if enabled
                preferences = getattr(bill.user, 'userpreferences', None)
                if preferences and preferences.bill_reminders and preferences.email_notifications:
                    send_bill_reminder_email.delay(bill.user.id, title, message)
                
                reminders_sent += 1
    
    return f"Sent {reminders_sent} bill reminders"


@shared_task
def send_bill_reminder_email(user_id, title, message):
    """Send bill reminder email to user"""
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            subject=title,
            message=message,
            from_email='noreply@expensetracker.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
        return f"Bill reminder email sent to {user.email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@shared_task
def generate_monthly_reports():
    """Generate and send monthly financial reports"""
    today = timezone.now().date()
    if today.day != 1:  # Only run on first day of month
        return "Monthly reports only generated on 1st of month"
    
    last_month = today.replace(day=1) - timedelta(days=1)
    users_with_reports = User.objects.filter(
        userpreferences__monthly_reports=True,
        userpreferences__email_notifications=True
    )
    
    reports_sent = 0
    for user in users_with_reports:
        # Calculate last month's statistics
        income = Transaction.objects.filter(
            user=user,
            trans_type='income',
            date__year=last_month.year,
            date__month=last_month.month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        expenses = Transaction.objects.filter(
            user=user,
            trans_type='expense',
            date__year=last_month.year,
            date__month=last_month.month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        savings = income - expenses
        
        # Get financial health score
        health_score = getattr(user, 'financialhealthscore', None)
        score = health_score.score if health_score else 0
        
        # Create notification
        title = f"Monthly Report - {last_month.strftime('%B %Y')}"
        message = f"""
        Monthly Financial Summary:
        • Income: ${income:,.2f}
        • Expenses: ${expenses:,.2f}
        • Net Savings: ${savings:,.2f}
        • Financial Health Score: {score}/100
        """
        
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type='monthly_summary',
            priority='low'
        )
        
        # Send email report
        send_monthly_report_email.delay(user.id, title, message, income, expenses, savings, score)
        reports_sent += 1
    
    return f"Generated {reports_sent} monthly reports"


@shared_task
def send_monthly_report_email(user_id, title, message, income, expenses, savings, score):
    """Send monthly report email with detailed statistics"""
    try:
        user = User.objects.get(id=user_id)
        
        # Render HTML email template
        html_message = render_to_string('emails/monthly_report.html', {
            'user': user,
            'income': income,
            'expenses': expenses,
            'savings': savings,
            'score': score,
        })
        
        send_mail(
            subject=title,
            message=message,
            from_email='noreply@expensetracker.com',
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Monthly report email sent to {user.email}"
    except Exception as e:
        return f"Failed to send monthly report: {str(e)}"


@shared_task
def check_savings_goal_milestones():
    """Check for savings goal milestones and create celebrations"""
    goals = SavingsGoal.objects.filter(status='active')
    
    milestones_created = 0
    for goal in goals:
        progress = goal.progress_percentage
        
        # Check for milestone achievements (25%, 50%, 75%, 100%)
        milestones = [25, 50, 75, 100]
        for milestone in milestones:
            if progress >= milestone:
                # Check if milestone notification already exists
                existing = Notification.objects.filter(
                    user=goal.user,
                    notification_type='goal_milestone',
                    title__contains=f"{milestone}% of {goal.name}"
                ).exists()
                
                if not existing:
                    if milestone == 100:
                        title = f"🎉 Goal Achieved: {goal.name}"
                        message = f"Congratulations! You've reached your savings goal of ${goal.target_amount}!"
                        goal.status = 'completed'
                        goal.completed_at = timezone.now()
                        goal.save()
                    else:
                        title = f"🎯 Milestone Reached: {milestone}% of {goal.name}"
                        message = f"Great progress! You've saved ${goal.current_amount} towards your ${goal.target_amount} goal."
                    
                    Notification.objects.create(
                        user=goal.user,
                        title=title,
                        message=message,
                        notification_type='goal_milestone',
                        priority='medium'
                    )
                    milestones_created += 1
    
    return f"Created {milestones_created} goal milestone notifications"


@shared_task
def detect_unusual_spending():
    """Detect unusual spending patterns and alert users"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    users = User.objects.all()
    alerts_created = 0
    
    for user in users:
        # Calculate average daily spending for last month
        monthly_expenses = Transaction.objects.filter(
            user=user,
            trans_type='expense',
            date__gte=month_ago,
            date__lt=week_ago
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        avg_daily_spending = monthly_expenses / 23 if monthly_expenses > 0 else Decimal('0')
        
        # Calculate this week's daily spending
        weekly_expenses = Transaction.objects.filter(
            user=user,
            trans_type='expense',
            date__gte=week_ago
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        days_this_week = (today - week_ago).days or 1
        weekly_daily_avg = weekly_expenses / days_this_week
        
        # Alert if spending is 50% higher than usual
        if avg_daily_spending > 0 and weekly_daily_avg > (avg_daily_spending * Decimal('1.5')):
            increase_percent = ((weekly_daily_avg - avg_daily_spending) / avg_daily_spending) * 100
            
            title = "⚠️ Unusual Spending Detected"
            message = f"Your daily spending this week (${weekly_daily_avg:.2f}) is {increase_percent:.0f}% higher than usual (${avg_daily_spending:.2f})"
            
            # Check if alert already sent this week
            existing = Notification.objects.filter(
                user=user,
                notification_type='unusual_spending',
                created_at__gte=week_ago
            ).exists()
            
            if not existing:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='unusual_spending',
                    priority='medium'
                )
                alerts_created += 1
    
    return f"Created {alerts_created} unusual spending alerts"
