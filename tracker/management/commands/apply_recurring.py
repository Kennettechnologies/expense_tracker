from django.core.management.base import BaseCommand
from tracker.models import RecurringTransaction, Transaction
from django.utils import timezone
from datetime import timedelta, date


def add_months(src_date, months):
    month = src_date.month - 1 + months
    year = src_date.year + month // 12
    month = month % 12 + 1
    day = min(src_date.day, 28)  # avoid month-end issues, keep simple
    return date(year, month, day)


class Command(BaseCommand):
    help = 'Apply due recurring transactions up to today'

    def handle(self, *args, **options):
        today = timezone.now().date()
        due = RecurringTransaction.objects.filter(active=True, next_date__lte=today)
        created = 0
        for rule in due:
            # create one occurrence for each due date (advance next_date iteratively)
            while rule.next_date and rule.next_date <= today:
                t = Transaction(
                    user=rule.user,
                    amount=rule.amount,
                    category=rule.category,
                    account=rule.account,
                    trans_type=rule.trans_type,
                    date=rule.next_date,
                    description=rule.description,
                    tags=rule.tags,
                )
                t.save()
                created += 1
                # advance next_date
                if rule.frequency == 'daily':
                    rule.next_date = rule.next_date + timedelta(days=1)
                elif rule.frequency == 'weekly':
                    rule.next_date = rule.next_date + timedelta(weeks=1)
                elif rule.frequency == 'monthly':
                    rule.next_date = add_months(rule.next_date, 1)
                elif rule.frequency == 'yearly':
                    rule.next_date = add_months(rule.next_date, 12)
                # stop if end_date reached
                if rule.end_date and rule.next_date > rule.end_date:
                    rule.active = False
                    break
            rule.save()
        self.stdout.write(self.style.SUCCESS(f'Created {created} transactions from recurrings'))
