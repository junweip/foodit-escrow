Setup:
pip install -r requirements.txt to install every package listed into your virtual environment

PaymentIntent -> transfer from buyer to Stripe WITHOUT money transfer; solely for dashboard visualization
Transfer -> transfer from Stripe to runner(supplier) WITHOUT money transfer; solely for dashboard visualization
Charge -> actual money transfer

In Stripe test mode, when you create a PaymentIntent (even if it succeeds),
your platform’s available balance does not actually increase automatically.
The test PaymentIntent simulates a payment, but it does not move real or test funds into your available balance.

Buyers: Customers (for payments)
Runners: Connected Accounts (for payouts; optionally also Customers if you want to track their payments)