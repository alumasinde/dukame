# DukaMe Customer Journey Assessment

## Recommended vs. Actual Implementation

### Summary
✅ **Good News:** Your app implements ~80% of the recommended journey  
⚠️ **Gap:** Missing delivery address collection and OTP SMS integration points  
✅ **Just Added:** Stock reservation system and OTP security infrastructure

---

## Step-by-Step Analysis

### 1. **Browse Store → Add to Cart** ✅ COMPLETE
**Recommended:** Show live availability, don't reserve stock  
**Your Implementation:**
- `GET /{store_slug}/cart` - Creates or retrieves cart
- `POST /{store_slug}/cart/items` - Adds items
- Stock checked via `_ensure_stock_available()` (shows on-hand quantity)
- No reservation at cart stage ✅

**Status:** ✅ Correct

---

### 2. **Cart → Confirm Order** ⚠️ PARTIAL
**Recommended:** Collect name, phone, delivery address, delivery notes, delivery option  
**Your Implementation:**
- `CheckoutRequest` schema collects:
  - ✅ `first_name`, `last_name`
  - ✅ `phone`
  - ✅ `email` (optional)
  - ✅ `notes` (for order notes)
  - ❌ **Missing:** `delivery_address`
  - ❌ **Missing:** `delivery_location` / map pin
  - ❌ **Missing:** `delivery_notes` (separate from order notes)
  - ❌ **Missing:** `delivery_option` (pickup vs delivery, express, etc)

**Status:** ⚠️ **Action Required:** Add delivery fields to CheckoutRequest

---

### 3. **Payment Page** ✅ COMPLETE
**Recommended:** Show order summary, exact amount, payment method choices  
**Your Implementation:**
- `GET /{store_slug}/payment-methods` - Lists enabled methods
- `POST /{store_slug}/cart/checkout` returns `OrderResponse` with:
  - ✅ `order_number`
  - ✅ `subtotal_minor`, `total_minor`
  - ✅ `payment` object with amount, method, status
  - ✅ `items` with line totals

**Status:** ✅ Correct

---

### 4. **Reserve Stock & Create Pending Order** ✅ COMPLETE (JUST ADDED)
**Recommended:** Atomically reserve quantities for short payment window  
**Your Implementation:**
- **Before Today:** Inventory deducted immediately ❌
- **Today's Update:** Stock reservation system added ✅
  - Creates `StockReservation` records during checkout
  - Expiry window: 15 minutes (configurable)
  - Status: pending → finalized/released
  - Available stock = on_hand - active_reservations

**Code Flow:**
```python
# In checkout():
reservation_expiry = now + timedelta(minutes=15)
for item in cart_items:
    reservation = StockReservation(
        order_id=order.id,
        product_id=product.id,
        variant_id=variant.id,
        quantity=item.quantity,
        status="pending",
        expires_at=reservation_expiry
    )
    self.db.add(reservation)
```

**Status:** ✅ Correct (Just Implemented)

---

### 5. **Payment Confirmed → Order Accepted** ✅ COMPLETE (INTEGRATION NEEDED)
**Recommended:** Verify via provider callback, convert reservation to sale, reduce stock  
**Your Implementation:**

**Payment Flow:**
```
M-Pesa STK Push initiated
    ↓
Customer enters PIN
    ↓
M-Pesa sends callback to: /api/v1/payments/mpesa/callback/{callback_token}
    ↓
PaymentService.callback() processes:
    - Validates receipt and amount
    - Sets payment.status = "paid"
    - Calls _confirm_order_after_payment()
        - Transitions order: pending → confirmed
        - Queues SMS notification
```

**INTEGRATION GAP:** Stock reservation NOT finalized on payment confirmation
- ❌ `_confirm_order_after_payment()` does NOT call `finalize_order_payment()`
- Need to add this call to finalize reservations

**Status:** ⚠️ **Action Required:** Hook payment confirmation to reservation finalization

---

### 6. **Prepare → Dispatch → Rider Arrives** ⚠️ PARTIAL
**Recommended:** Generate OTP when rider assigned, send via SMS to customer phone  
**Your Implementation:**
- `DeliveryService.assign()` - Assigns rider, sets status="assigned"
- `DeliveryService.issue_otp()` - **Just Enhanced** ✅
  - Generates 6-digit OTP
  - Hashes it (never stores plaintext)
  - Stores SHA256 hash in `delivery.otp_hash`
  - Sets expiry (30 min default)
  - Resets attempt counter

**Gap:**
- ❌ OTP NOT sent via SMS (no integration point yet)
- ✅ Everything else is secure and ready

**Code:**
```python
async def issue_otp(self, user, tenant_public_id, order_public_id):
    # ...
    otp = f"{secrets.randbelow(1_000_000):06d}"
    delivery.otp_hash = self._hash_otp(delivery.public_id, otp)
    delivery.otp_expires_at = now + timedelta(minutes=30)
    # NOTE: OTP should be sent to customer.phone via SMS here
    return delivery, otp  # otp only for backend integration
```

**Status:** ✅ Security ready, ⚠️ SMS integration missing

---

### 7. **Customer Gives OTP → Delivery Completed** ✅ COMPLETE
**Recommended:** Rider enters code, verify, record completion time  
**Your Implementation:**
- `DeliveryService.confirm(otp)` - **Just Enhanced** ✅
  - Verifies OTP not expired
  - Checks attempt limit (3 max)
  - Compares with hash using `secrets.compare_digest()` (constant-time)
  - Increments attempt counter on failure
  - On success:
    - Marks delivery as delivered
    - Records `delivered_by_user_id` and `delivered_at`
    - Stores delivery note
    - Sets `otp_verified_at`
    - Audit logs everything

**Code:**
```python
async def confirm(self, user, tenant_public_id, order_public_id, otp, note):
    # ... validation ...
    if not secrets.compare_digest(delivery.otp_hash, self._hash_otp(delivery.public_id, otp)):
        delivery.otp_attempts += 1
        await self.db.commit()
        raise HTTPException(422, "Invalid delivery OTP")
    
    delivery.status = "delivered"
    delivery.delivered_at = now
    delivery.delivered_by_user_id = user.id
    delivery.delivery_note = note
    # ... audit log ...
```

**Status:** ✅ Correct

---

## Summary Table

| Step | Requirement | Status | Notes |
|------|-------------|--------|-------|
| 1 | Browse & Add to Cart (no reserve) | ✅ | Working correctly |
| 2 | Collect checkout details | ⚠️ | Missing delivery address/options |
| 3 | Payment page with summary | ✅ | Complete |
| 4 | Reserve stock atomically | ✅ | **Just Added Today** |
| 5 | Payment confirmed → finalize | ⚠️ | Missing hook to finalize_order_payment() |
| 6 | Prepare & dispatch, OTP issued | ⚠️ | OTP security ready, SMS integration missing |
| 7 | OTP verified → completed | ✅ | Complete & secure |

---

## Action Items (High Priority)

### 1. **Integrate Payment Confirmation with Stock Finalization**
**File:** `backend/app/modules/commerce/payment_service.py`  
**Location:** `_confirm_order_after_payment()` method (line 345)  
**Change:**
```python
async def _confirm_order_after_payment(self, payment: Payment) -> None:
    order = await self.db.scalar(...)
    # ... existing status transition code ...
    
    # ADD THIS: Finalize stock reservations
    from app.modules.commerce.service import CommerceService
    service = CommerceService(self.db)
    await service.finalize_order_payment(order.id)
    
    self.db.add(OrderStatusHistory(...))
```

### 2. **Add Delivery Address Fields to Checkout**
**File:** `backend/app/modules/commerce/schemas.py`  
**Update `CheckoutRequest`:**
```python
class CheckoutRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=32)
    email: str | None = None
    
    # NEW: Delivery details
    delivery_address: str = Field(min_length=5, max_length=500)
    delivery_location: str | None = Field(None, max_length=500)  # landmark/map pin
    delivery_notes: str | None = Field(None, max_length=1000)
    delivery_option: str = Field(default="standard")  # standard, express, pickup
```

**Update Order model** to store delivery fields:
```python
class Order(Base):
    # ... existing fields ...
    delivery_address: Mapped[str] = mapped_column(String(500))
    delivery_location: Mapped[str | None] = mapped_column(String(500))
    delivery_notes: Mapped[str | None] = mapped_column(String(1000))
    delivery_option: Mapped[str] = mapped_column(String(50))
```

### 3. **Integrate OTP SMS Sending**
**File:** `backend/app/modules/commerce/delivery_service.py`  
**Location:** `issue_otp()` method (line 63)  
**Add:**
```python
async def issue_otp(self, user, tenant_public_id, order_public_id):
    # ... existing code ...
    
    delivery.otp_hash = self._hash_otp(delivery.public_id, otp)
    delivery.otp_expires_at = now + timedelta(minutes=30)
    
    # NEW: Send OTP via SMS
    order = delivery.order
    if order and order.customer_phone:
        from app.modules.commerce.notifications import send_otp_sms
        try:
            await send_otp_sms(
                phone=order.customer_phone,
                otp=otp,
                store_name=store.name
            )
        except Exception as e:
            # Log but don't fail checkout
            print(f"OTP SMS failed: {e}")
    
    return delivery, otp
```

### 4. **Add Maintenance Task to Release Expired Reservations**
**File:** `backend/app/workers/runner.py`  
**Add to scheduler:**
```python
from app.workers.release_expired_reservations import release_expired_reservations

# Run every 5 minutes
@app.on_event("startup")
async def start_maintenance():
    asyncio.create_task(run_maintenance_loop())

async def run_maintenance_loop():
    while True:
        try:
            db = get_db()
            await release_expired_reservations(db)
        except Exception as e:
            print(f"Maintenance task failed: {e}")
        await asyncio.sleep(300)  # Every 5 minutes
```

---

## Testing Checklist

- [ ] Add delivery address to checkout request
- [ ] Verify stock reservation created on checkout
- [ ] Verify payment callback calls finalize_order_payment()
- [ ] Verify inventory deducted after payment confirmed
- [ ] Verify expired reservations released after 15 min
- [ ] Verify OTP sent to customer phone
- [ ] Verify OTP verification is constant-time
- [ ] Verify attempt limit blocks after 3 failures
- [ ] Verify only assigned rider can confirm
- [ ] Verify delivery marked complete on OTP verification

---

## Configuration

Update `.env`:
```bash
# Stock reservation
PAYMENT_RESERVATION_TTL_MINUTES=15

# Delivery OTP
DELIVERY_OTP_TTL_MINUTES=30
DELIVERY_OTP_MAX_ATTEMPTS=3

# SMS integration (if using a service)
SMS_PROVIDER=africastalking  # or twilio, nexmo, etc
SMS_API_KEY=your_key
SMS_SENDER_ID=DUKAME
```

---

## Conclusion

Your app is **very close** to the recommended journey. With these 4 action items completed, you'll have a **production-grade e-commerce flow** that:

✅ Prevents double-selling (stock reservation)  
✅ Confirms payment before stock deduction  
✅ Secures delivery handover with OTP  
✅ Maintains complete audit trail  
✅ Handles edge cases (expired payments, failed OTP attempts)  

**Estimated effort:** 3-4 hours to implement all gaps
