# CarpoolGo – College Carpool App

A simple web app where college students can share rides.

## Setup & Run

```bash
# 1. Install Flask
pip install flask

# 2. Run the app
python app.py

# 3. Open in browser
http://127.0.0.1:5000
```

## How It Works

### As a Driver
1. Register / Login
2. Click **+ Ride** → enter start location, add via points, set time & seats
3. Go to **Requests** to accept/reject passenger offers

### As a Passenger
1. Register / Login
2. Click **Search** → type your location
3. If a ride passes through your area, send a price offer
4. Check **Dashboard** to see if driver accepted

## Project Structure
```
carpool/
├── app.py              ← Flask backend (all routes)
├── requirements.txt    ← Just flask
├── carpool.db          ← SQLite DB (auto-created on first run)
├── templates/
│   ├── base.html       ← Nav bar + shared layout
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── create_ride.html
│   ├── search.html
│   └── driver_requests.html
└── static/
    └── style.css       ← All styles
```

## Database Tables
- **users** – id, name, email, password
- **rides** – id, driver_id, start_location, time, seats, active
- **route_points** – id, ride_id, location, order_number
- **requests** – id, ride_id, passenger_id, offer_price, status
