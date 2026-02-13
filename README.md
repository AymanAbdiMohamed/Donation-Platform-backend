# SheNeeds - Donation Platform Backend

Flask REST API for the SheNeeds Donation Platform - connecting donors with verified charities focused on menstrual health education and access.

## About

SheNeeds is a donation platform designed to bridge the gap between generous donors and verified charitable organizations working to improve menstrual health education and access. The backend provides a robust REST API with role-based access control, secure authentication, and comprehensive donation management.

### Key Features

- **JWT Authentication** - Secure user authentication with role-based access control
- **Multi-Role System** - Support for donors, charities, and administrators
- **Charity Verification** - Application and approval process for charities
- **M-Pesa Integration** - STK Push payment processing for secure KES donations
- **Donation Management** - Track and manage donations with detailed records
- **Dashboard Analytics** - Real-time statistics for charities and administrators
- **Error Handling** - Comprehensive error handling with standardized responses
- **Database Migrations** - Flask-Migrate for version-controlled database schema
- **Email Notifications** - Automated receipt delivery via email
- **API Documentation** - Well-documented REST endpoints

## Tech Stack

- **Flask 3.0** - Web framework
- **Flask-SQLAlchemy** - ORM
- **Flask-JWT-Extended** - JWT authentication
- **Flask-CORS** - Cross-origin support
- **Flask-Migrate** - Database migrations
- **PostgreSQL** - Production database
- **SQLite** - Development database
- **Gunicorn** - Production WSGI server

## Architecture

```
app/
├── __init__.py          # Flask application factory
├── config.py            # Configuration classes (Dev/Test/Prod)
├── extensions.py        # Flask extensions (db, jwt, cors, migrate)
├── models/              # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py          # User model with auth methods
│   ├── charity.py       # Charity + CharityApplication models
│   └── donation.py      # Donation model
├── routes/              # API route blueprints
│   ├── __init__.py
│   ├── health.py        # Health check endpoint
│   ├── auth.py          # Authentication routes
│   ├── donor.py         # Donor routes
│   ├── charity.py       # Charity routes
│   ├── admin.py         # Admin routes
│   ├── payment.py       # M-Pesa callback handlers
│   └── donations_api.py # Donation API endpoints
├── services/            # Business logic layer
│   ├── __init__.py
│   ├── user_service.py
│   ├── charity_service.py
│   ├── donation_service.py
│   └── payment_service.py
├── auth/                # Authentication & authorization
│   ├── __init__.py
│   ├── decorators.py    # Role-based access decorators
│   └── handlers.py      # JWT error handlers
├── errors/              # Error handling
│   ├── __init__.py
│   ├── responses.py     # Standardized error responses
│   └── handlers.py      # Global error handlers
└── utils/               # Utility functions
    ├── __init__.py
    ├── mpesa.py         # M-Pesa API client
    ├── email.py         # Email service
    └── helpers.py
```

## Quick Start

### Local Development

```bash
cd Donation-Platform-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.local .env

# Run database migrations
flask db upgrade

# Create admin user
python seed_admin.py

# Seed with test data (development only)
python seed_db.py

# Run the server
python run_app.py
```

Server runs at `http://localhost:5000`

### Environment Configuration

Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/app.db

# CORS
CORS_ORIGINS=http://localhost:5173

# M-Pesa Configuration
MPESA_CONSUMER_KEY=your-consumer-key
MPESA_CONSUMER_SECRET=your-consumer-secret
MPESA_SHORTCODE=your-shortcode
MPESA_PASSKEY=your-passkey
MPESA_ENV=sandbox
MPESA_STK_CALLBACK_URL=your-callback-url
MPESA_TIMEOUT_URL=your-timeout-url

# Email Configuration (Mailtrap for development)
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USERNAME=your-mailtrap-username
MAIL_PASSWORD=your-mailtrap-password
MAIL_DEFAULT_SENDER=noreply@sheneeds.org

# Admin Account
ADMIN_EMAIL=admin@sheneeds.org
```

### Production Deployment

For production deployment on Railway or similar platforms:

1. Set environment variables in your hosting platform
2. Use PostgreSQL database (set `DATABASE_URL`)
3. Set `FLASK_ENV=production`
4. Configure proper CORS origins
5. Use strong secret keys
6. Enable HTTPS

## API Endpoints

### Health Check
- `GET /health` - Service health check

### Authentication (`/auth`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/register` | Register new user | No |
| POST | `/login` | Login, get JWT | No |
| GET | `/me` | Get current user | Yes |

### Donor Routes (`/donor`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/charities` | List active charities (paginated) | Donor |
| GET | `/charities/:id` | Get charity details | Donor |
| GET | `/donations` | Get donation history (paginated) | Donor |
| GET | `/dashboard` | Get donor stats | Donor |

### Donation API (`/api/donations`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/mpesa` | Initiate M-Pesa STK Push | Donor |
| GET | `/status/:id` | Poll donation status | Donor |

### M-Pesa Payment (`/api/mpesa`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/callback` | M-Pesa callback handler | No (Safaricom) |
| POST | `/timeout` | M-Pesa timeout handler | No (Safaricom) |
| GET | `/query/:checkout_id` | Query payment status | No |

### Charity Routes (`/charity`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/apply` | Submit application | Charity |
| GET | `/application` | Get application status | Charity |
| GET | `/profile` | Get charity profile | Charity |
| PUT | `/profile` | Update profile | Charity |
| GET | `/donations` | Get received donations | Charity |
| GET | `/dashboard` | Get dashboard stats | Charity |

### Admin Routes (`/admin`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/users` | List all users (paginated) | Admin |
| GET | `/applications` | List applications (paginated) | Admin |
| GET | `/applications/:id` | Get application | Admin |
| POST | `/applications/:id/approve` | Approve application | Admin |
| POST | `/applications/:id/reject` | Reject application | Admin |
| GET | `/charities` | List all charities (paginated) | Admin |
| GET | `/charities/:id` | Get charity details | Admin |
| DELETE | `/charities/:id` | Deactivate charity | Admin |
| POST | `/charities/:id/activate` | Reactivate charity | Admin |
| GET | `/stats` | Platform statistics | Admin |

### Public Routes
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/charities` | List active charities (paginated) | No |
| GET | `/charities/:id` | Get charity details | No |

## Authentication

All protected routes require a JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `/auth/login` or `/auth/register`.

### Roles
- **donor** - Can browse charities and make donations
- **charity** - Can manage charity profile and view donations
- **admin** - Full platform management access

## Payment Integration

### M-Pesa STK Push

The platform integrates with Safaricom's M-Pesa Daraja API for secure payment processing:

1. **Initiate Payment** - POST to `/api/donations/mpesa` with amount and phone number
2. **STK Push Sent** - User receives payment prompt on their phone
3. **User Confirms** - User enters M-Pesa PIN to complete payment
4. **Callback Received** - Safaricom sends payment confirmation to callback URL
5. **Donation Updated** - System marks donation as PAID and sends receipt email
6. **Status Query** - Frontend can poll `/api/mpesa/query/:checkout_id` for status

### Payment Flow

```
Frontend → Backend → M-Pesa API → User's Phone
                ↓
         Donation Created (PENDING)
                ↓
         User Enters PIN
                ↓
    M-Pesa → Callback → Backend
                ↓
         Donation Updated (PAID)
                ↓
         Receipt Email Sent
```

## Email Notifications

The platform sends automated email receipts for successful donations using Flask-Mail:

- **Development**: Uses Mailtrap for testing
- **Production**: Configure SMTP settings for production email service

Receipt emails include:
- Donation amount
- Charity name
- M-Pesa receipt number
- Transaction date
- Donor information (if not anonymous)

## Database Migrations

```bash
# Apply pending migrations
flask db upgrade

# Create new migration after model changes
flask db migrate -m "Description of changes"

# Downgrade one migration
flask db downgrade

# View migration history
flask db history
```

## Test Credentials

After seeding with `python seed_db.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@test.com` | `admin123` |
| Donor | `donor@test.com` | `donor123` |
| Charity | `charity@test.com` | `charity123` |

## Dependencies

- Flask 3.0.0
- Flask-SQLAlchemy (ORM)
- Flask-JWT-Extended (Auth)
- Flask-CORS (Cross-origin)
- Flask-Migrate (Migrations)
- Flask-Mail (Email)
- Flask-Limiter (Rate limiting)
- python-dotenv (Environment variables)
- Werkzeug (Password hashing)
- requests (HTTP client)
- gunicorn (Production server)

## Development

### Running with Frontend

1. Start the backend:
   ```bash
   cd Donation-Platform-backend
   python run_app.py
   ```

2. Start the frontend (in another terminal):
   ```bash
   cd Donation-Platform-frontend
   npm run dev
   ```

3. Access the app at `http://localhost:5173`

### Adding New Routes

1. Create route file in `app/routes/`
2. Register blueprint in `app/routes/__init__.py`
3. Add service methods in `app/services/` if needed

## Troubleshooting

### Common Issues

**Database schema out of sync**
```bash
# Apply all pending migrations
flask db upgrade

# For development, reset database
rm instance/app.db
flask db upgrade
```

**JWT token errors**
- Ensure `JWT_SECRET_KEY` is set in your environment
- Check token expiration time (default 24 hours)
- Verify token is included in Authorization header

**CORS issues**
- Check that `CORS_ORIGINS` includes your frontend URL
- Default allows `http://localhost:5173`

**M-Pesa integration issues**
- Verify credentials are correct
- Check callback URL is publicly accessible (use ngrok for local testing)
- Review M-Pesa logs in application output

## Production Checklist

- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `FLASK_ENV=production`
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Configure production email service
- [ ] Set up M-Pesa production credentials
- [ ] Configure database backups
- [ ] Set up monitoring and error tracking

## License

MIT

---

Built for menstrual health advocacy
