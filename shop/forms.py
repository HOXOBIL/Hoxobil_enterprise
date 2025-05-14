# shop/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm, AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

CustomUser = get_user_model() # Get your custom user model

class CustomUserCreationForm(DjangoUserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'appearance-none rounded-md relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm'})
    )
    first_name = forms.CharField(
        label=_("First name"), 
        max_length=150, 
        widget=forms.TextInput(attrs={'autocomplete': 'given-name', 'class': 'appearance-none rounded-md relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm'})
    )
    last_name = forms.CharField(
        label=_("Last name"), 
        max_length=150, 
        widget=forms.TextInput(attrs={'autocomplete': 'family-name', 'class': 'appearance-none rounded-md relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm'})
    )
    referral_code = forms.CharField(
        label=_("Referral Code (Optional)"),
        max_length=12,
        required=False, # Make it optional
        widget=forms.TextInput(attrs={'placeholder': 'Enter referral code if you have one', 'class': 'appearance-none rounded-md relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm'})
    )

    class Meta(DjangoUserCreationForm.Meta):
        model = CustomUser
        fields = ("email", "first_name", "last_name") # Username is not needed here as email is the username field

    def save(self, commit=True):
        user = super().save(commit=False)
        # Email is already set as it's the username field
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class EmailAuthenticationForm(DjangoAuthenticationForm):
    username = forms.EmailField( # Override username to be an EmailField
        label=_("Email"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email', 'class': 'appearance-none rounded-md relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm'})
    )
    # Password field is inherited and fine as is
