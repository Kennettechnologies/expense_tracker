from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Transaction, Budget, RecurringTransaction, TransactionSplit
from .models import TransactionTemplate, SavingsGoal, GoalContribution, Bill


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'currency', 'timezone', 'profile_pic')


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ('amount', 'category', 'account', 'transfer_account', 'trans_type', 'date', 'time', 'description', 'receipt', 'tags')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }


class CSVUploadForm(forms.Form):
    file = forms.FileField()


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ('name', 'category', 'amount', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ('amount', 'category', 'account', 'trans_type', 'description', 'tags', 'frequency', 'next_date', 'end_date', 'active')
        widgets = {
            'next_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TransactionSplitForm(forms.ModelForm):
    class Meta:
        model = TransactionSplit
        fields = ('category', 'amount')


class TransactionTemplateForm(forms.ModelForm):
    class Meta:
        model = TransactionTemplate
        fields = ('name', 'amount', 'category', 'account', 'trans_type', 'description', 'tags')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ('name', 'target_amount', 'target_date', 'description')
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class GoalContributionForm(forms.ModelForm):
    class Meta:
        model = GoalContribution
        fields = ('amount', 'description')
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Optional note about this contribution'}),
        }


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ('name', 'amount', 'category', 'account', 'due_date', 'frequency', 'description', 'reminder_days', 'auto_pay')
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class BulkTransactionForm(forms.Form):
    """Form for bulk operations on transactions"""
    action = forms.ChoiceField(choices=[
        ('delete', 'Delete Selected'),
        ('change_category', 'Change Category'),
        ('add_tags', 'Add Tags'),
        ('export', 'Export Selected'),
    ])
    category = forms.ModelChoiceField(queryset=None, required=False, empty_label="Select Category")
    tags = forms.CharField(max_length=200, required=False, help_text="Comma-separated tags")
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.all()


class AdvancedSearchForm(forms.Form):
    """Advanced search form for transactions"""
    query = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search description...'}))
    category = forms.ModelChoiceField(queryset=None, required=False, empty_label="All Categories")
    trans_type = forms.ChoiceField(choices=[('', 'All Types')] + list(Transaction.TRAN_TYPES), required=False)
    account = forms.ModelChoiceField(queryset=None, required=False, empty_label="All Accounts")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    amount_min = forms.DecimalField(required=False, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'Min amount'}))
    amount_max = forms.DecimalField(required=False, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'Max amount'}))
    tags = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search tags...'}))
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category, Account
            self.fields['category'].queryset = Category.objects.all()
            self.fields['account'].queryset = Account.objects.filter(user=user)
