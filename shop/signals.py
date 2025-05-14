# shop/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile, WinningCode 
from django.utils import timezone # *** ADDED THIS IMPORT ***

# The post_save signal for UserProfile creation is in models.py to handle UserProfile creation and referral_code generation.

def process_successful_referral(referrer_user_profile):
    """
    Called when referrer_user_profile successfully refers a new user.
    Increments their referral count and checks for digit unlock.
    """
    if referrer_user_profile:
        referrer_user_profile.referral_count += 1
        # We only need to save the fields that changed
        referrer_user_profile.save(update_fields=['referral_count', 'updated_at'])
        print(f"Referral count for {referrer_user_profile.user.username} incremented to {referrer_user_profile.referral_count}")

        # Check if they reached the threshold and haven't unlocked a digit yet
        if referrer_user_profile.referral_count >= 30 and not referrer_user_profile.unlocked_first_digit:
            # Find an unclaimed winning code (e.g., the first one available)
            # This logic can be refined (e.g., random, specific code for referrals, or ensure code has 6 digits)
            winning_code_to_reveal = WinningCode.objects.filter(is_claimed=False).order_by('created_at').first()
            
            if winning_code_to_reveal and len(winning_code_to_reveal.code) > 0: # Ensure code is not empty
                referrer_user_profile.unlocked_first_digit = winning_code_to_reveal.code[0]
                referrer_user_profile.unlocked_digit_from_code = winning_code_to_reveal
                referrer_user_profile.digit_unlocked_at = timezone.now() # Use the imported timezone
                referrer_user_profile.save(update_fields=['unlocked_first_digit', 'unlocked_digit_from_code', 'digit_unlocked_at', 'updated_at'])
                print(f"Unlocked first digit '{referrer_user_profile.unlocked_first_digit}' for {referrer_user_profile.user.username} from code {winning_code_to_reveal.code}")
            else:
                print(f"User {referrer_user_profile.user.username} reached 30 referrals, but no unclaimed winning codes available to reveal a digit (or code was empty).")
