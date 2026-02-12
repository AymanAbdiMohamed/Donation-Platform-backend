#!/bin/bash

# M-Pesa Quick Test Script
# This script helps you quickly test your M-Pesa integration from the command line

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:5000}"

echo -e "${BLUE}🚀 M-Pesa Integration Quick Test${NC}"
echo "Backend URL: $BACKEND_URL"
echo "============================================="

# Function to print section headers
print_section() {
    echo -e "\n${YELLOW}$1${NC}"
    echo "----------------------------------------"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Basic health check
print_section "1. Testing Basic Health Check"
if curl -s "$BACKEND_URL/health" > /dev/null; then
    print_success "Backend is running"
else
    print_error "Backend is not accessible at $BACKEND_URL"
    exit 1
fi

# Test 2: M-Pesa health check
print_section "2. Testing M-Pesa Configuration"
mpesa_response=$(curl -s "$BACKEND_URL/health/mpesa" || echo "ERROR")

if echo "$mpesa_response" | grep -q '"status":"healthy"'; then
    print_success "M-Pesa is configured and accessible"
    echo "$mpesa_response" | python3 -m json.tool 2>/dev/null || echo "$mpesa_response"
elif echo "$mpesa_response" | grep -q '"status":"unhealthy"'; then
    print_error "M-Pesa configuration issue detected"  
    echo "$mpesa_response" | python3 -m json.tool 2>/dev/null || echo "$mpesa_response"
    echo -e "\n${YELLOW}💡 Quick fixes:${NC}"
    echo "1. Check your .env file has correct M-Pesa credentials"
    echo "2. Ensure MPESA_ENV=sandbox"
    echo "3. Get fresh credentials from https://developer.safaricom.co.ke"
    exit 1
else
    print_error "Could not check M-Pesa health"
    echo "Response: $mpesa_response"  
    exit 1
fi

# Test 3: Manual OAuth test  
print_section "3. Testing OAuth Token Generation"
echo "You can also test OAuth manually with curl..."
echo "Make sure these environment variables are set in your .env:"
echo "- MPESA_CONSUMER_KEY"
echo "- MPESA_CONSUMER_SECRET"

# Test 4: Available endpoints
print_section "4. Available M-Pesa Endpoints"
echo "✓ Health check: GET $BACKEND_URL/health/mpesa"
echo "✓ STK Push: POST $BACKEND_URL/api/donations/mpesa (requires JWT auth)"
echo "✓ Status check: GET $BACKEND_URL/api/donations/status/<checkout_id> (requires JWT auth)"
echo "✓ Callback: POST $BACKEND_URL/api/donations/mpesa/callback (Safaricom only)"

print_section "5. Test with Python Script"
echo "For comprehensive testing, run:"
echo "  cd $(dirname "$0")"
echo "  python test_mpesa.py"

print_section "✅ Quick Test Complete"
if echo "$mpesa_response" | grep -q '"status":"healthy"'; then
    print_success "Your M-Pesa integration is working!"
    echo -e "\n${GREEN}🎉 You can now:${NC}"
    echo "1. Test donations through your frontend"
    echo "2. Use the test_mpesa.py script for detailed testing"
    echo "3. Monitor logs during transactions"
else
    print_error "M-Pesa integration needs attention"
    echo "Check the error messages above and fix the configuration"
    exit 1
fi