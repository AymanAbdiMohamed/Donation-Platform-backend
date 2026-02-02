# Donation Platform - Backend

Barebones Flask API for the Donation Platform.

## Structure

```
backend/
├── app.py           # Flask app + route registration
├── models.py        # ALL models (User, CharityApplication, Charity, Donation)
├── routes.py        # ALL routes (Auth, Donor, Charity, Admin)
├── auth.py          # JWT + role decorators
├── db.py            # SQLAlchemy init
├── config.py        # Dev config (SQLite default)
├── run.py           # Entry point
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env file (optional - defaults work for dev)
cp .env.example .env

# Run the server
python run.py
```

Server runs at `http://localhost:5000`

## Dependencies

- Flask 3.0.0
- Flask-SQLAlchemy (ORM)
- Flask-JWT-Extended (Auth)
- Flask-Cors (CORS)
- Flask-Migrate (Migrations)
- python-dotenv (Env vars)

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login, get JWT
- `GET /api/auth/me` - Get current user

### Donor
- `GET /api/donor/charities` - List active charities
- `POST /api/donor/donate` - Make donation
- `GET /api/donor/donations` - Donation history

### Charity
- `POST /api/charity/apply` - Submit application
- `GET /api/charity/application` - Get application status
- `GET /api/charity/profile` - Get charity profile
- `PUT /api/charity/profile` - Update profile
- `GET /api/charity/donations` - Received donations
- `GET /api/charity/dashboard` - Dashboard stats

### Admin
- `GET /api/admin/applications` - List applications
- `POST /api/admin/applications/:id/approve` - Approve
- `POST /api/admin/applications/:id/reject` - Reject
- `GET /api/admin/charities` - List all charities
- `DELETE /api/admin/charities/:id` - Deactivate charity
- `GET /api/admin/stats` - Platform stats

## Models

- **User** - donors, charities, admins (role field)
- **CharityApplication** - pending applications
- **Charity** - approved charities
- **Donation** - donation records
