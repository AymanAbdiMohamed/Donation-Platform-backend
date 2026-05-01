# SheNeeds — Donation Platform Backend

Flask REST API for the SheNeeds Donation Platform, connecting donors with verified charities focused on menstrual health education and access in Kenya.

## Tech Stack

- **Flask 3.0** + Flask-SQLAlchemy + Flask-Migrate
- **Flask-JWT-Extended** — JWT authentication with role-based access
- **Flask-Limiter** — rate limiting
- **Flask-APScheduler** — recurring donation processing
- **PostgreSQL** (production) / **SQLite** (development)
- **Gunicorn** — production WSGI server
- **M-Pesa Daraja API** — STK Push payments (sandbox + mock mode)

## Architecture

```
app/
├── __init__.py          # Application factory
├── config.py            # Config classes (Dev/Test/Prod) + env var loading
├── extensions.py        # Extension singletons (db, jwt, limiter, scheduler)
├── models/
│   ├── user.py          # User — roles: donor, charity, admin
│   ├── charity.py       # Charity + CharityApplication (approval workflow)
│   ├── donation.py      # Donation — amount in cents, STK Push tracking
│   ├── subscription.py  # Recurring donation schedules
│   ├── story.py         # Impact stories posted by charities
│   ├── beneficiary.py   # Beneficiaries + inventory tracking
│   └── charity_document.py  # Uploaded verification documents
├── routes/
│   ├── auth.py          # /auth — register, login, /me
│   ├── donor.py         # /donor — dashboard, charities, donations
│   ├── charity.py       # /charity — application, profile, donations
│   ├── admin.py         # /admin — users, applications, stats, analytics
│   ├── donations_api.py # /api/donations — M-Pesa initiation, status polling
│   ├── payment.py       # /api/mpesa — Safaricom callbacks
│   ├── public.py        # /charities — unauthenticated browsing
│   ├── stories.py       # /stories — impact stories
│   ├── beneficiaries.py # /beneficiaries — charity beneficiary management
│   ├── pesapal.py       # /api/pesapal — Pesapal gateway (alternative)
│   └── health.py        # /health — service health check
├── services/
│   ├── user_service.py
│   ├── charity_service.py
│   ├── donation_service.py
│   ├── payment_service.py
│   ├── receipt_service.py
│   └── scheduler_service.py  # Recurring donation processing
├── auth/
│   ├── decorators.py    # @role_required, @admin_required, etc.
│   └── handlers.py      # Custom JWT error responses
├── errors/
│   ├── responses.py     # bad_request(), not_found(), unauthorized(), etc.
│   └── handlers.py      # Global 404/500 handlers
└── utils/
    ├── mpesa.py         # MpesaClient — token cache, STK push, callback parsing
    ├── mock_mpesa.py    # Mock callback simulator (background thread, 5s delay)
    ├── pesapal.py       # PesapalClient
    ├── email.py         # EmailService (SMTP)
    ├── file_upload.py   # Secure file upload handler
    └── helpers.py       # utc_now(), normalise_phone()
```

## Local Development

```bash
cd Donation-Platform-backend

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY, JWT_SECRET_KEY, MPESA_MOCK_MODE=True

# Seed database with test data (drops and recreates tables)
python seed_db.py

# Start development server
python -m flask run --port 5000
```

Server runs at `http://localhost:5000`

## Environment Variables

See `.env.example` for the full list. Minimum required for local dev:

```env
SECRET_KEY=any-random-string
JWT_SECRET_KEY=any-random-string
MPESA_MOCK_MODE=True
CORS_ORIGINS=http://localhost:5173
```

For production, also set:

```env
DATABASE_URL=postgresql://user:pass@host/dbname
FLASK_ENV=production
CORS_ORIGINS=https://your-frontend-domain.com
```

## API Endpoints

### Authentication (`/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | No | Register — roles: `donor`, `charity` |
| POST | `/login` | No | Returns JWT access token |
| GET | `/me` | Yes | Current user profile |

### Donor (`/donor`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/charities` | Donor | Active charities |
| GET | `/charities/:id` | Donor | Charity details |
| GET | `/dashboard` | Donor | Stats + recent donations |
| GET | `/donations` | Donor | Paginated donation history |
| GET | `/donations/:id/status` | Donor | Poll donation status |
| GET | `/donations/:id/receipt` | Donor | Receipt data |

### Donations API (`/api/donations`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/mpesa` | Donor | Initiate M-Pesa STK Push |
| POST | `/manual` | Donor | Create manual (paybill) donation |
| POST | `/:id/submit-code` | Donor | Submit M-Pesa transaction code |
| GET | `/:id/status` | Donor | Poll by donation ID |
| GET | `/status/:checkout_id` | Donor | Poll by checkout request ID |

### M-Pesa Callbacks (`/api/mpesa`) — called by Safaricom, not frontend
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/callback` | No | STK Push result |
| POST | `/timeout` | No | Timeout notification |
| GET | `/query/:checkout_id` | No | Query Safaricom directly |

### Charity (`/charity`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/apply` | Charity | Submit application (multipart) |
| GET | `/application` | Charity | Application status |
| GET | `/profile` | Charity | Charity profile |
| PUT | `/profile` | Charity | Update profile |
| GET | `/donations` | Charity | Received donations |
| GET | `/dashboard` | Charity | Stats + recent donations |

### Admin (`/admin`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users` | Admin | All users (paginated) |
| POST | `/users/:id/deactivate` | Admin | Deactivate user |
| POST | `/users/:id/activate` | Admin | Reactivate user |
| GET | `/applications` | Admin | All applications (paginated) |
| POST | `/applications/:id/approve` | Admin | Approve + create charity |
| POST | `/applications/:id/reject` | Admin | Reject with reason |
| GET | `/charities` | Admin | All charities (paginated) |
| DELETE | `/charities/:id` | Admin | Deactivate charity |
| POST | `/charities/:id/activate` | Admin | Reactivate charity |
| GET | `/stats` | Admin | Platform-wide statistics |
| GET | `/analytics` | Admin | 30-day trends + top charities |

### Public (no auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/charities` | Active charities (paginated) |
| GET | `/charities/:id` | Charity details |
| GET | `/health` | Service health |

## Authentication

All protected routes require:
```
Authorization: Bearer <access_token>
```

Tokens are obtained from `/auth/login` or `/auth/register`. They embed the user's role as a JWT claim — checked by `@role_required()` without a DB lookup on every request.

## M-Pesa Payment Flow

```
Frontend → POST /api/donations/mpesa
         → DonationService.initiate_mpesa_donation()
         → MpesaClient.initiate_stk_push()
         → Donation created (status=PENDING)
         ← checkout_request_id returned

[User approves on phone]

Safaricom → POST /api/mpesa/callback
          → DonationService.process_stk_callback()
          → Donation updated (status=SUCCESS + receipt_number)

Frontend polls → GET /api/donations/status/:checkout_id → sees SUCCESS
```

**Mock mode** (`MPESA_MOCK_MODE=True`): skips Safaricom entirely, spawns a background thread that fires the success callback after 5 seconds. Full end-to-end flow without real credentials.

## Test Credentials

After running `python seed_db.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@sheneeds.dev` | `admin123` |
| Donor | `donor@sheneeds.dev` | `donor123` |
| Donor | `wanjiku@example.co.ke` | `password123` |

## Database Migrations

```bash
flask db upgrade          # Apply pending migrations
flask db migrate -m "..."  # Generate migration after model changes
flask db downgrade         # Roll back one migration
```

For local dev, `seed_db.py` drops and recreates all tables directly — faster than running migrations during development.

## Production Checklist

- [ ] Strong random `SECRET_KEY` and `JWT_SECRET_KEY` (use `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] PostgreSQL database configured via `DATABASE_URL`
- [ ] `FLASK_ENV=production`
- [ ] `CORS_ORIGINS` set to your frontend domain (no wildcard)
- [ ] HTTPS on the backend
- [ ] M-Pesa callback URL publicly accessible
- [ ] Rate limit storage switched from `memory://` to Redis URL (`RATELIMIT_STORAGE_URI`)
- [ ] Log rotation configured

## License

MIT
