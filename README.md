# Supply Chain Management System

A comprehensive supply chain management system built with Django, including inventory management, supplier management, and purchase order processing.

## Features

- Inventory Management
- Supplier Management
- Purchase Order Processing
- Stock Level Tracking
- Financial Analytics
- Reporting System
- API Integration
- Email Notifications

## Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (for Celery)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd scm_system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=scm_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Start the development server:
```bash
python manage.py runserver
```

## Configuration

### Email Settings

Add the following to your `.env` file:
```
EMAIL_HOST=your-smtp-server
EMAIL_PORT=587
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=True
```

### Celery Configuration

1. Start Redis server
2. Run Celery worker:
```bash
celery -A scm_system worker -l info
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin/`
2. Login with your superuser credentials
3. Start managing your inventory!

## API Documentation

API endpoints are available at:
- REST API: `http://localhost:8000/api/`
- FastAPI: `http://localhost:8000/fastapi/docs`

## Scheduled Tasks

The system includes several scheduled tasks:
- Daily stock level checks
- Weekly inventory reports
- Monthly supplier performance analysis

Configure these in the Django admin interface.

## Testing

Run the test suite:
```bash
python manage.py test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
