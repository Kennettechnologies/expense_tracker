from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import io
import os


class FinancialReportGenerator:
    """Generate PDF financial reports with charts and tables"""
    
    def __init__(self, user, start_date=None, end_date=None):
        self.user = user
        self.start_date = start_date or timezone.now().date().replace(day=1)
        self.end_date = end_date or timezone.now().date()
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e')
        ))
    
    def generate_monthly_report(self):
        """Generate comprehensive monthly financial report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build story (content)
        story = []
        
        # Title
        title = Paragraph(f"Monthly Financial Report - {self.start_date.strftime('%B %Y')}", 
                         self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Summary section
        story.extend(self._build_summary_section())
        story.append(Spacer(1, 20))
        
        # Income vs Expenses chart
        story.extend(self._build_income_expense_chart())
        story.append(Spacer(1, 20))
        
        # Category breakdown
        story.extend(self._build_category_breakdown())
        story.append(Spacer(1, 20))
        
        # Transaction details
        story.extend(self._build_transaction_details())
        story.append(Spacer(1, 20))
        
        # Budget analysis
        story.extend(self._build_budget_analysis())
        story.append(Spacer(1, 20))
        
        # Goals progress
        story.extend(self._build_goals_progress())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_summary_section(self):
        """Build financial summary section"""
        from ..models import Transaction, Account
        
        # Calculate totals
        income = Transaction.objects.filter(
            user=self.user, trans_type='income',
            date__gte=self.start_date, date__lte=self.end_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        expenses = Transaction.objects.filter(
            user=self.user, trans_type='expense',
            date__gte=self.start_date, date__lte=self.end_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        net_savings = income - expenses
        total_balance = Account.objects.filter(user=self.user).aggregate(
            Sum('balance'))['balance__sum'] or Decimal('0')
        
        # Create summary table
        summary_data = [
            ['Metric', 'Amount'],
            ['Total Income', f'${income:,.2f}'],
            ['Total Expenses', f'${expenses:,.2f}'],
            ['Net Savings', f'${net_savings:,.2f}'],
            ['Current Balance', f'${total_balance:,.2f}'],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return [
            Paragraph("Financial Summary", self.styles['SectionHeader']),
            summary_table
        ]
    
    def _build_income_expense_chart(self):
        """Build income vs expenses bar chart"""
        from ..models import Transaction
        
        # Get monthly data for the last 6 months
        chart_data = []
        labels = []
        
        for i in range(6):
            month_start = (self.start_date.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start.replace(month=month_start.month+1) - timedelta(days=1)) if month_start.month < 12 else month_start.replace(year=month_start.year+1, month=1) - timedelta(days=1)
            
            income = Transaction.objects.filter(
                user=self.user, trans_type='income',
                date__gte=month_start, date__lte=month_end
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            expenses = Transaction.objects.filter(
                user=self.user, trans_type='expense',
                date__gte=month_start, date__lte=month_end
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            chart_data.append((float(income), float(expenses)))
            labels.append(month_start.strftime('%b %Y'))
        
        # Create bar chart
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        chart.data = list(zip(*chart_data))
        chart.categoryAxis.categoryNames = labels
        chart.valueAxis.valueMin = 0
        chart.bars[0].fillColor = colors.HexColor('#2ecc71')  # Income - Green
        chart.bars[1].fillColor = colors.HexColor('#e74c3c')  # Expenses - Red
        
        drawing.add(chart)
        
        return [
            Paragraph("Income vs Expenses Trend", self.styles['SectionHeader']),
            drawing
        ]
    
    def _build_category_breakdown(self):
        """Build category spending breakdown"""
        from ..models import Transaction
        
        # Get category data
        categories = Transaction.objects.filter(
            user=self.user, trans_type='expense',
            date__gte=self.start_date, date__lte=self.end_date
        ).values('category__name').annotate(
            total=Sum('amount'), count=Count('id')
        ).order_by('-total')[:10]
        
        if not categories:
            return [Paragraph("No expense data available for category breakdown", 
                            self.styles['Normal'])]
        
        # Create table
        table_data = [['Category', 'Amount', 'Transactions', 'Percentage']]
        total_expenses = sum(cat['total'] for cat in categories)
        
        for cat in categories:
            percentage = (cat['total'] / total_expenses * 100) if total_expenses > 0 else 0
            table_data.append([
                cat['category__name'] or 'Uncategorized',
                f"${cat['total']:,.2f}",
                str(cat['count']),
                f"{percentage:.1f}%"
            ])
        
        category_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return [
            Paragraph("Top Spending Categories", self.styles['SectionHeader']),
            category_table
        ]
    
    def _build_transaction_details(self):
        """Build recent transactions table"""
        from ..models import Transaction
        
        # Get recent transactions
        transactions = Transaction.objects.filter(
            user=self.user,
            date__gte=self.start_date, date__lte=self.end_date
        ).order_by('-date', '-created_at')[:20]
        
        if not transactions:
            return [Paragraph("No transactions found for this period", 
                            self.styles['Normal'])]
        
        # Create table
        table_data = [['Date', 'Type', 'Category', 'Amount', 'Description']]
        
        for trans in transactions:
            table_data.append([
                trans.date.strftime('%m/%d/%Y'),
                trans.get_trans_type_display(),
                trans.category.name if trans.category else 'N/A',
                f"${trans.amount:,.2f}",
                (trans.description[:30] + '...') if len(trans.description) > 30 else trans.description
            ])
        
        trans_table = Table(table_data, colWidths=[1*inch, 0.8*inch, 1.2*inch, 1*inch, 2*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        return [
            Paragraph("Recent Transactions", self.styles['SectionHeader']),
            trans_table
        ]
    
    def _build_budget_analysis(self):
        """Build budget performance analysis"""
        from ..models import Budget, Transaction
        
        budgets = Budget.objects.filter(user=self.user)
        if not budgets:
            return [Paragraph("No budgets configured", self.styles['Normal'])]
        
        # Create budget analysis table
        table_data = [['Budget', 'Allocated', 'Spent', 'Remaining', 'Status']]
        
        for budget in budgets:
            spent = Transaction.objects.filter(
                user=self.user,
                category=budget.category,
                trans_type='expense',
                date__gte=budget.start_date or self.start_date,
                date__lte=budget.end_date or self.end_date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            remaining = budget.amount - spent
            percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
            
            if percentage > 100:
                status = "Over Budget"
            elif percentage > 90:
                status = "Near Limit"
            elif percentage > 75:
                status = "On Track"
            else:
                status = "Under Budget"
            
            table_data.append([
                budget.name,
                f"${budget.amount:,.2f}",
                f"${spent:,.2f}",
                f"${remaining:,.2f}",
                status
            ])
        
        budget_table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
        budget_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return [
            Paragraph("Budget Analysis", self.styles['SectionHeader']),
            budget_table
        ]
    
    def _build_goals_progress(self):
        """Build savings goals progress"""
        from ..models import SavingsGoal
        
        goals = SavingsGoal.objects.filter(user=self.user, status='active')
        if not goals:
            return [Paragraph("No active savings goals", self.styles['Normal'])]
        
        # Create goals table
        table_data = [['Goal', 'Target', 'Current', 'Progress', 'Target Date']]
        
        for goal in goals:
            progress_pct = goal.progress_percentage
            target_date = goal.target_date.strftime('%m/%d/%Y') if goal.target_date else 'N/A'
            
            table_data.append([
                goal.name,
                f"${goal.target_amount:,.2f}",
                f"${goal.current_amount:,.2f}",
                f"{progress_pct:.1f}%",
                target_date
            ])
        
        goals_table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
        goals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return [
            Paragraph("Savings Goals Progress", self.styles['SectionHeader']),
            goals_table
        ]


def generate_pdf_report(user, report_type='monthly', start_date=None, end_date=None):
    """Generate PDF report and return HTTP response"""
    generator = FinancialReportGenerator(user, start_date, end_date)
    
    if report_type == 'monthly':
        buffer = generator.generate_monthly_report()
        filename = f"monthly_report_{generator.start_date.strftime('%Y_%m')}.pdf"
    else:
        # Add other report types here
        buffer = generator.generate_monthly_report()
        filename = f"financial_report_{generator.start_date.strftime('%Y_%m_%d')}.pdf"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(buffer.getvalue())
    buffer.close()
    
    return response
