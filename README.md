# Flasky Inventory Management System

A Flask-based inventory management system with order processing, payment handling, and email confirmation features.

## Features

- **Product Management**: Create and manage product inventory
- **Order Processing**: Create orders with multiple items
- **Payment System**: Process payments with email confirmations
- **Stock Management**: Automatic stock deduction on orders

### Prerequisites

- Python 3.13+
- Git
- Email account (Gmail recommended for email features)

### Clone the Repository

#### Using SSH (Recommended for developers)

```bash
git clone git@github.com:mohmdloai/flasky.git
cd flasky
```

#### Using HTTPS

```bash
git clone https://github.com/mohmdloai/flasky.git
cd flasky
```

## Installation

### 1. Create Virtual Environment

#### On Linux/macOS

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

#### On Windows

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Command Prompt)
.venv\Scripts\activate


### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```


## Configuration

### 1. Create Environment File

Create a `.env` file in the project root:

```env
# Email Configuration (Required for order confirmations)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com


### 1. Initialize Database

```bash
python app.py
```

The application will:

- Create the SQLite database automatically
- Run on `http://localhost:3000`

### 2. Access the API

The API will be available at:

- Base URL: `http://localhost:3000/api`
- Products: `http://localhost:3000/api/products`

## Testing

### Run All Tests

```bash
pytest tests/test_order_process.py -v -s


### Order Processing Workflow

The complete order processing involves three main API calls:

#### 1. Create Products (Setup)

First, create some products in your inventory:

```bash
curl -X POST http://localhost:3000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 14",
    "price": 999.99,
    "stock": 10
  }'
```

#### 2. Create Order with Items

**Endpoint:** `POST /api/orders`

Create a new order with multiple items:

```bash
curl -X POST http://localhost:3000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "items": [
      {
        "product_id": 1,
        "quantity": 2
      },
      {
        "product_id": 2,
        "quantity": 1
      }
    ]
  }'
```

**Response:**

```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john.doe@example.com",
  "payment_status": "pending",
  "shipping_status": "pending",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "quantity": 2,
      "product": {
        "id": 1,
        "name": "iPhone 14",
        "price": 999.99,
        "stock": 8
      }
    }
  ],
  "total_amount": 1999.98
}
```

#### 3. Add Items to Existing Order (Optional)

**Endpoint:** `POST /api/orders/{order_id}/items`

Add more items to an existing unpaid order:

```bash
curl -X POST http://localhost:3000/api/orders/1/items \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 3,
    "quantity": 1
  }'
```

#### 4. Process Payment

**Endpoint:** `POST /api/orders/{order_id}/pay`

Process payment for the order:

```bash
curl -X POST http://localhost:3000/api/orders/1/pay \
  -H "Content-Type: application/json"
```

**Response:**

```json
{
  "message": "Payment successful",
  "payment_reference": "Ref_ABC123XYZ9",
  "order": {
    "id": 1,
    "payment_status": "paid",
    "payment_reference": "Ref_ABC123XYZ9",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "total_amount": 1999.98
  }
}
```
