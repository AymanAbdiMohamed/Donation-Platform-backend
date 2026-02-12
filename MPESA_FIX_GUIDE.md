# 🔧 M-Pesa Integration Fix Guide

## 🚨 Issue Identified

Your M-Pesa integration is failing with:
```
"errorCode": "400.008.01",
"errorMessage": "Invalid Authentication passed"
```

This happens because of incorrect or invalid sandbox credentials.

## ✅ Solution Steps

### 1. Get Valid Sandbox Credentials

1. Go to [Safaricom Developer Portal](https://developer.safaricom.co.ke/)
2. Sign in or create an account
3. Create a new sandbox application
4. Note down your **Consumer Key** and **Consumer Secret**

### 2. Update Your Environment File

Replace the credentials in your `.env.production` file:

```bash
# M-Pesa Daraja Sandbox Configuration
MPESA_ENV=sandbox
MPESA_CONSUMER_KEY=your_actual_consumer_key_here
MPESA_CONSUMER_SECRET=your_actual_consumer_secret_here
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed191

# Callback URLs - update to your Railway backend
MPESA_STK_CALLBACK_URL=https://web-production-63323.up.railway.app/api/donations/mpesa/callback
MPESA_TIMEOUT_URL=https://web-production-63323.up.railway.app/api/donations/mpesa/timeout
```

### 3. Test Your Configuration

#### Option A: Quick Shell Script Test
```bash
cd /root/projects/DonationPlatform/Donation-Platform-backend
./test_mpesa.sh
```

#### Option B: Python Test Script
```bash
cd /root/projects/DonationPlatform/Donation-Platform-backend
python test_mpesa.py
```

#### Option C: Manual curl Test
```bash
# Test M-Pesa health endpoint
curl -X GET "http://localhost:5000/health/mpesa"

# Should return:
# {
#   "status": "healthy",
#   "mpesa": "connected",
#   "environment": "sandbox",
#   "message": "M-Pesa connection successful"
# }
```

### 4. Test OAuth Token Generation

After updating credentials, test the token generation:

```bash
cd /root/projects/DonationPlatform/Donation-Platform-backend
python -c "
from app import create_app
from app.config import Config
from app.utils.mpesa import MpesaClient

app = create_app(Config)
with app.app_context():
    client = MpesaClient()
    token = client.get_access_token()
    print(f'✅ Success! Token: {token[:20]}...')
"
```

### 5. Test STK Push (Sandbox)

```bash
# Test with Safaricom test number
python -c "
from app import create_app
from app.config import Config
from app.utils.mpesa import MpesaClient

app = create_app(Config)
with app.app_context():
    client = MpesaClient()
    result = client.initiate_stk_push(
        phone='254708374149',  # Safaricom test number
        amount=1,
        reference='TEST',
        description='Test payment'
    )
    print(f'Result: {result}')
"
```

## 🔍 Debugging Tips

### Check Your Current Credentials

```python
import os
print(f"Consumer Key: {os.getenv('MPESA_CONSUMER_KEY', 'NOT SET')[:8]}...")
print(f"Consumer Secret: {os.getenv('MPESA_CONSUMER_SECRET', 'NOT SET')[:8]}...")
print(f"Environment: {os.getenv('MPESA_ENV', 'NOT SET')}")
```

### Common Issues & Fixes

1. **Invalid Consumer Key/Secret**
   - Get fresh credentials from Safaricom Developer Portal
   - Ensure you're copying the sandbox credentials, not production

2. **Wrong Environment**
   - Set `MPESA_ENV=sandbox` for testing
   - Never use production credentials for testing

3. **Callback URL Issues**
   - Update callback URLs to your deployed Railway backend
   - Ensure URLs are accessible from the internet

## 🎯 Expected Results

After fixing credentials:

1. **Health Check**: `/health/mpesa` returns `"status": "healthy"`
2. **Token Generation**: OAuth tokens are generated successfully
3. **STK Push**: Payments can be initiated without 400 errors
4. **Callbacks**: Payment results are processed correctly

## 📱 Frontend Integration

Once backend is working, test through your frontend:

1. Go to your React app
2. Browse charities  
3. Try to make a donation
4. Check that STK push reaches your phone (sandbox test number)

## 🚀 Production Deployment

When ready for production:

1. Get production credentials from Safaricom
2. Set `MPESA_ENV=production`
3. Update callback URLs to production domain
4. Test with small amounts first

## 🛠️ Monitoring & Logs

Add logging to monitor M-Pesa transactions:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mpesa')

# This will show detailed logs of M-Pesa operations
```

## ❓ Need Help?

1. Check logs in `/var/log/` or Railway logs
2. Verify environment variables are loaded
3. Test with curl commands first
4. Use the Python test script for detailed debugging

---

**Remember**: The credentials in your current `.env.production` file appear to be invalid or expired. Get fresh ones from the Safaricom Developer Portal.