# M-Pesa Mock Mode - Demo Instructions

## ✅ Mock Mode is NOW ENABLED

Your donation platform now accepts **fake donations** with instant success - perfect for demos!

## How It Works

1. **User makes donation** → Frontend calls M-Pesa endpoint
2. **Backend simulates success** → No real M-Pesa API calls
3. **Donation marked as PAID** → Instantly (no waiting)
4. **Receipt email sent** → Via Mailtrap
5. **Shows in dashboards** → With dummy data

## What You'll See

**Donation Flow:**
- ✅ User enters amount and phone
- ✅ "Payment successful" message appears instantly
- ✅ Donation shows as PAID in database
- ✅ Receipt email sent to Mailtrap
- ✅ Appears in donor/charity dashboards

**Mock Data Generated:**
- Checkout Request ID: `ws_CO_<timestamp>_MOCK`
- Merchant Request ID: `GR_<timestamp>_MOCK`
- M-Pesa Receipt: `MOCK<timestamp>`
- Status: PAID (instant)

## Testing the Demo

1. **Start frontend**: `npm run dev`
2. **Make a donation**:
   - Select any charity
   - Enter any amount (e.g., 100 KES)
   - Enter any phone number (e.g., 0712345678)
   - Click "Pay"
3. **See instant success** ✅
4. **Check dashboards**:
   - Donor dashboard shows donation
   - Charity dashboard shows received donation
   - Admin dashboard shows all donations

## Production Deployment

Add this to your server environment file (`.env`):
```
MPESA_MOCK_MODE="True"
```

This allows your deployed app to work without real M-Pesa credentials.

## Switching to Real M-Pesa Later

When you get valid Safaricom credentials:
1. Set `MPESA_MOCK_MODE="False"`
2. Update M-Pesa credentials
3. Redeploy

Your platform is ready for demo! 🎉
