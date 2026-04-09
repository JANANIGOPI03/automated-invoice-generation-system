# invoicing/forms.py
from django import forms
from db import get_user_by_email


class RegisterForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Full name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'})
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    role = forms.ChoiceField(
        choices=[('customer', 'Customer'), ('admin', 'Admin')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_by_email(email):
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class CustomerForm(forms.Form):
    name = forms.CharField(max_length=255, widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=50, required=False, widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    password = forms.CharField(
        min_length=6, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    billing_address = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 2}))


class ProductForm(forms.Form):
    name = forms.CharField(max_length=255, widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    description = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 3}))
    unit_price = forms.DecimalField(
        max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    is_available = forms.BooleanField(
        required=False,
        initial=True,
        label="Available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=255, widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=50, required=False, widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    billing_address = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 2}))
