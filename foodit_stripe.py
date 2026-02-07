import os
from dotenv import load_dotenv
import stripe
import time

load_dotenv()

# 1. SETUP: Add your Stripe Secret Key (Test Mode)
stripe.api_key = os.getenv('STRIPE_API_KEY') 

def simulate_escrow_flow():
    # ---------------------------------------------------------
    # INITIAL SETUP: Add a large test balance to the platform
    # ---------------------------------------------------------
    print("\n0. Adding initial test balance to platform...")
    try:
        initial_balance = 1000000  # $10,000.00 in cents
        initial_charge = stripe.Charge.create(
            amount=initial_balance,
            currency="sgd",
            source="tok_bypassPending",
            description="Initial test funds for platform balance"
        )
        print(f"   ✅ Initial test funds added. Charge ID: {initial_charge.id}")
    except Exception as e:
        print(f"   ❌ Initial test fund charge failed: {e}")
        return
    
    print("--- 🏁 Starting Escrow Simulation ---")

    # ---------------------------------------------------------
    # STEP 1: Onboard the Runner (Create a Connected Account)
    # ---------------------------------------------------------
    # In a real app, the runner would go through a Stripe hosted onboarding flow (OAuth).
    # For this script, we create a 'Custom' account to simulate a runner immediately.
    print("\n1. Creating Runner's Connected Account...")
    
    try:
        runner_account = stripe.Account.create(
            type="custom",
            country="SG",
            email="runner_test@example.com",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="individual",
            business_profile={
                "mcc": "5734",
                "url": "https://accessible.stripe.com",
                "product_description": "Delivery Services SG",
            },
            # Singapore Identity Data (Test Mode)
            individual={
                "first_name": "Jun Wei",
                "last_name": "Png",
                "full_name_aliases": ["Ah Kow Tan", "A.K. Tan"],
                "nationality": "SG",
                "email": "junwei@example.com",
                "phone": "+6581234567",
                "dob": {"day": 1, "month": 1, "year": 1990},
                "address": {
                    "line1": "10 Collyer Quay",
                    "postal_code": "049315",
                    "city": "Singapore",
                    "country": "SG",
                },
                "id_number": "S0000000Z", 
            },
            tos_acceptance={
                "date": int(time.time()),
                "ip": "127.0.0.1", 
            },
            external_account="btok_sg"
        )

        runner_id = runner_account.id

        print(f"   ✅ Runner Onboarded! ID: {runner_id}")
    except Exception as e:
        print(f"   ❌ Error creating account: {e}")
        return
    
    # ---------------------------------------------------------
    # STEP 2: The "Escrow" Hold (Charge the Buyer)
    # ---------------------------------------------------------
    # We charge the buyer $100.00. The funds go to YOU (The Platform).
    # This acts as the "Escrow" state because you hold the money, not the runner.
    print("\n2. Buyer pays $10. The Platform holds funds (Escrow)...")
    
    amount_to_charge = 1000  # $10.00 in cents
    
    try:
        # We use a PaymentIntent. 
        # 'pm_card_visa' is a Stripe test token for a valid Visa card.
        payment = stripe.PaymentIntent.create(
            amount=amount_to_charge,
            currency="sgd",
            payment_method_types=["card"],
            payment_method="pm_card_visa", 
            confirm=True, # Charges the card immediately
        )
        print(f"   ✅ Payment Captured by Platform. Status: {payment.status}")
        print(f"   💰 Funds are now held in your Platform Balance.")
    except Exception as e:
        print(f"   ❌ Payment failed: {e}")
        return

    # ---------------------------------------------------------
    # STEP 3: The Work (Simulation)
    # ---------------------------------------------------------
    print("\n... 🚚 Runner is delivering the item (Waiting 3 seconds) ...")
    time.sleep(3)
    
    # ---------------------------------------------------------
    # STEP 4: The Release (Transfer to Runner)
    # ---------------------------------------------------------
    # Buyer confirms delivery. We now transfer funds to the Runner.
    # Usually, the platform keeps a fee. Let's say Runner gets $90, Platform keeps $10.
    print("\n4. Delivery confirmed! Releasing funds to Runner...")
    
    amount_to_runner = 900 # $9.00 in cents

    try:
        transfer = stripe.Transfer.create(
            amount=amount_to_runner,
            currency="sgd",
            destination=runner_id,
            description="Payout for delivered goods",
        )
        print(f"   ✅ Funds Released! Transfer ID: {transfer.id}")
        print(f"   💵 ${amount_to_runner/100} sent to Runner ({runner_id})")
        print(f"   🏦 ${ (amount_to_charge - amount_to_runner)/100 } kept by Platform as fee.")
    except Exception as e:
        print(f"   ❌ Transfer failed: {e}")

    print("\n--- 🎉 Escrow Simulation Complete ---")

if __name__ == "__main__":
    simulate_escrow_flow()