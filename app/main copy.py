import time
from typing import Optional

import stripe
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import settings

# ---------------------------------------------------------------------------
# Stripe init
# ---------------------------------------------------------------------------
stripe.api_key = settings.STRIPE_API_KEY

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="FoodIT Escrow Service")


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------
class OnboardRunnerRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    phone: str  # E.164 format, e.g. "+6581234567"
    #dob_day: int
    #dob_month: int
    #dob_year: int
    #address_line1: str
    #postal_code: str
    #id_number: str  # NRIC / FIN for SG


class OnboardRunnerResponse(BaseModel):
    runner_account_id: str
    message: str


class CreateEscrowRequest(BaseModel):
    amount: float  # Amount in dollars
    payment_method: str = "pm_card_visa"  # Stripe test token default
    metadata: Optional[dict] = None


class CreateEscrowResponse(BaseModel):
    payment_intent_id: str
    status: str
    amount: float
    currency: str
    message: str


class ReleaseEscrowRequest(BaseModel):
    runner_account_id: str
    amount: float  # Total charged amount in dollars
    platform_fee_percent: Optional[int] = None  # Override default fee
    description: str = "Payout for delivered goods"
    metadata: Optional[dict] = None


class ReleaseEscrowResponse(BaseModel):
    transfer_id: str
    amount_to_runner: float
    platform_fee: float
    currency: str
    message: str


class RefundRequest(BaseModel):
    payment_intent_id: str
    amount: Optional[float] = None  # None = full refund
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    refund_id: str
    status: str
    amount: float
    message: str


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "FoodIT Escrow Service is running", "env": settings.ENV}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# 1. Onboard a runner (create Stripe Connected Account)
# ---------------------------------------------------------------------------
@app.post("/runners/onboard", response_model=OnboardRunnerResponse)
def onboard_runner(req: OnboardRunnerRequest):
    """Create a Stripe Connected Account for a runner so they can receive payouts."""
    try:
        runner_account = stripe.Account.create(
            type="custom",
            country="SG",
            email=req.email,
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
            individual={
                "first_name": req.first_name,
                "last_name": req.last_name,
                "full_name_aliases": ["Test", "Test"],
                "nationality": "SG",
                "email": req.email,
                "phone": req.phone,
                "dob": {
                    # "day": req.dob_day,
                    # "month": req.dob_month,
                    # "year": req.dob_year,
                    "day": "1",
                    "month": "1",
                    "year": "2000",
                },
                "address": {
                    # "line1": req.address_line1,
                    # "postal_code": req.postal_code,
                    "line1": "Sample Address",
                    "postal_code": "Sample Postal",
                    "city": "Singapore",
                    "country": "SG",
                },
                #"id_number": req.id_number,
                "id_number": "S0000000Z",
            },
            
            tos_acceptance={
                "date": int(time.time()),
                "ip": "127.0.0.1",
            },
            external_account="btok_sg",
        )
        return OnboardRunnerResponse(
            runner_account_id=runner_account.id,
            message="Runner onboarded successfully",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# 2. Create an escrow payment (charge the buyer, platform holds funds)
# ---------------------------------------------------------------------------
@app.post("/escrow/create", response_model=CreateEscrowResponse)
def create_escrow(req: CreateEscrowRequest):
    """Charge the buyer. Funds are held by the platform (escrow state)."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    amount_cents = int(req.amount * 100)
    try:
        payment = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="sgd",
            payment_method_types=["card"],
            payment_method="pm_card_visa",
            confirm=True,
            metadata=req.metadata or {},
        )
        return CreateEscrowResponse(
            payment_intent_id=payment.id,
            status=payment.status,
            amount=round(amount_cents / 100, 2),
            currency="sgd",
            message="Payment captured. Funds held in platform balance (escrow).",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# 3. Release escrow funds to the runner
# ---------------------------------------------------------------------------
@app.post("/escrow/release", response_model=ReleaseEscrowResponse)
def release_escrow(req: ReleaseEscrowRequest):
    """Transfer funds from platform balance to the runner's connected account."""
    # Convert amount from dollars to cents
    amount_cents = int(req.amount * 100)
    fee_pct = req.platform_fee_percent if req.platform_fee_percent is not None else settings.PLATFORM_FEE_PERCENT
    platform_fee_cents = int(amount_cents * fee_pct / 100)
    amount_to_runner_cents = amount_cents - platform_fee_cents

    if amount_to_runner_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount after fee must be positive")

    try:
        transfer = stripe.Transfer.create(
            amount=amount_to_runner_cents,
            currency=settings.CURRENCY,
            destination=req.runner_account_id,
            description=req.description,
            metadata=req.metadata or {},
        )
        return ReleaseEscrowResponse(
            transfer_id=transfer.id,
            amount_to_runner=round(amount_to_runner_cents / 100, 2),
            platform_fee=round(platform_fee_cents / 100, 2),
            currency=settings.CURRENCY,
            message=f"${amount_to_runner_cents / 100:.2f} released to runner. "
                    f"${platform_fee_cents / 100:.2f} kept as platform fee.",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# 4. Refund an escrow payment (dispute / cancellation)
# ---------------------------------------------------------------------------
@app.post("/escrow/refund", response_model=RefundResponse)
def refund_escrow(req: RefundRequest):
    """Refund a payment (full or partial) back to the buyer."""
    try:
        refund_params: dict = {"payment_intent": req.payment_intent_id}
        if req.amount is not None:
            refund_params["amount"] = int(req.amount * 100)
        if req.reason:
            refund_params["reason"] = req.reason

        refund = stripe.Refund.create(**refund_params)
        return RefundResponse(
            refund_id=refund.id,
            status=refund.status,
            amount=round(refund.amount / 100, 2),
            message="Refund processed successfully",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# 5. Seed platform test balance (test mode only)
# ---------------------------------------------------------------------------
@app.post("/escrow/seed-balance")
def seed_balance(amount: int = 1000000):
    """Add test funds to the platform balance. Only works in Stripe test mode."""
    if settings.ENV == "prod":
        raise HTTPException(status_code=403, detail="Seeding is disabled in production")

    try:
        amount_cents = int(amount * 100)
        charge = stripe.Charge.create(
            amount=amount_cents,
            currency=settings.CURRENCY,
            source="tok_bypassPending",
            description="Initial test funds for platform balance",
        )
        return {
            "charge_id": charge.id,
            "amount": round(amount_cents / 100, 2),
            "message": f"${amount:.2f} added to platform test balance",
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
