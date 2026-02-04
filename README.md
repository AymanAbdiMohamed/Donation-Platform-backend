# Donation Platform - Backend

Flask REST API for the Donation Platform.

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
│   └── admin.py         # Admin routes
├── services/            # Business logic layer
│   ├── __init__.py
│   ├── user_service.py
│   ├── charity_service.py
│   └── donation_service.py
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
    └── helpers.py
```

## Setup

```bash
cd Donation-Platform-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env

# Seed the database (optional)
python seed_db.py

# Run the server
python run_app.py
```

Server runs at `http://localhost:5000`

## Configuration

Environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | dev-secret-key |
| `JWT_SECRET_KEY` | JWT signing key | jwt-secret-key |
| `JWT_EXPIRES_HOURS` | Token expiration | 24 |
| `FLASK_ENV` | Environment (development/production) | development |
| `DATABASE_URL` | Full database URL | SQLite |
| `POSTGRES_HOST` | PostgreSQL host | - |
| `POSTGRES_USER` | PostgreSQL user | - |
| `POSTGRES_PASSWORD` | PostgreSQL password | - |
| `POSTGRES_DB` | PostgreSQL database | - |

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
| GET | `/charities` | List active charities | Donor |
| GET | `/charities/:id` | Get charity details | Donor |
| POST | `/donate` | Make a donation | Donor |
| GET | `/donations` | Get donation history | Donor |

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
| GET | `/users` | List all users | Admin |
| GET | `/applications` | List applications | Admin |
| GET | `/applications/:id` | Get application | Admin |
| POST | `/applications/:id/approve` | Approve application | Admin |
| POST | `/applications/:id/reject` | Reject application | Admin |
| GET | `/charities` | List all charities | Admin |
| GET | `/charities/:id` | Get charity details | Admin |
| DELETE | `/charities/:id` | Deactivate charity | Admin |
| POST | `/charities/:id/activate` | Reactivate charity | Admin |
| GET | `/stats` | Platform statistics | Admin |

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

## Models

### User
- `id`, `username`, `email`, `password_hash`, `role`, `is_active`, `created_at`

### Charity
- `id`, `name`, `description`, `user_id`, `is_active`, `created_at`

### CharityApplication
- `id`, `user_id`, `name`, `description`, `status`, `rejection_reason`, `created_at`, `reviewed_at`

### Donation
- `id`, `amount` (cents), `donor_id`, `charity_id`, `is_anonymous`, `is_recurring`, `message`, `created_at`

## Development

### Test Credentials (after seeding)
- Admin: `admin@test.com` / `admin123`
- Donor: `donor@test.com` / `donor123`
- Charity: `charity@test.com` / `charity123`

### Dependencies
- Flask 3.0.0
- Flask-SQLAlchemy (ORM)
- Flask-JWT-Extended (Auth)
- Flask-CORS (CORS)
- Flask-Migrate (Migrations)
- python-dotenv (Env vars)
- Werkzeug (Password hashing)

## License

MIT
