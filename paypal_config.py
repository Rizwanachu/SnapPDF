import os
import paypalrestsdk
from datetime import datetime, timedelta

# PayPal configuration
def configure_paypal():
    """Configure PayPal SDK"""
    paypalrestsdk.configure({
        "mode": "sandbox",  # Change to "live" for production
        "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
        "client_secret": os.environ.get('PAYPAL_CLIENT_SECRET')
    })

# Subscription plans
PREMIUM_PLAN_ID = "PREMIUM_MONTHLY"  # You'll need to create this in PayPal dashboard

def create_subscription_plan():
    """Create a subscription plan in PayPal (run this once to set up)"""
    plan = paypalrestsdk.Plan({
        "name": "PDF Tools Premium Monthly",
        "description": "Unlimited PDF processing with premium features",
        "type": "INFINITE",
        "payment_definitions": [{
            "name": "Premium Monthly Payment",
            "type": "REGULAR",
            "frequency": "MONTH",
            "frequency_interval": "1",
            "amount": {
                "value": "9.99",
                "currency": "USD"
            },
            "cycles": "0"  # Infinite
        }],
        "merchant_preferences": {
            "setup_fee": {
                "value": "0",
                "currency": "USD"
            },
            "return_url": f"{os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')}/subscription/success",
            "cancel_url": f"{os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')}/subscription/cancel",
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE",
            "max_fail_attempts": "3"
        }
    })
    
    if plan.create():
        print(f"Plan created successfully: {plan.id}")
        return plan.id
    else:
        print(f"Error creating plan: {plan.error}")
        return None

def create_subscription_agreement(plan_id, user_email, user_name):
    """Create a subscription agreement"""
    agreement = paypalrestsdk.Agreement({
        "name": "PDF Tools Premium Subscription",
        "description": "Monthly subscription for unlimited PDF processing",
        "start_date": (datetime.now() + timedelta(minutes=1)).isoformat() + "Z",
        "plan": {
            "id": plan_id
        },
        "payer": {
            "payment_method": "paypal",
            "payer_info": {
                "email": user_email
            }
        }
    })
    
    if agreement.create():
        return agreement
    else:
        print(f"Error creating agreement: {agreement.error}")
        return None

def execute_subscription_agreement(token):
    """Execute the subscription agreement after user approval"""
    agreement = paypalrestsdk.Agreement.find(token)
    if agreement.execute({"payer_id": token}):
        return agreement
    else:
        print(f"Error executing agreement: {agreement.error}")
        return None

def cancel_subscription(agreement_id, reason="User requested cancellation"):
    """Cancel a subscription"""
    agreement = paypalrestsdk.Agreement.find(agreement_id)
    cancel_note = {
        "cancel_note": reason
    }
    
    if agreement.cancel(cancel_note):
        return True
    else:
        print(f"Error canceling subscription: {agreement.error}")
        return False

def get_subscription_details(agreement_id):
    """Get subscription details"""
    try:
        agreement = paypalrestsdk.Agreement.find(agreement_id)
        return agreement
    except Exception as e:
        print(f"Error getting subscription details: {e}")
        return None