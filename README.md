# 🚗 CollegeSaathi – Carpool Web App

**Built for MLVTIANS, by an MLVTIAN.**

CollegeSaathi is a simple and smart carpooling web application designed exclusively for MLVTIANS. It helps students connect, share rides, and reduce travel costs while building a community.

---

## 🌟 Features

* 🔐 User Authentication (Register / Login)
* 🚘 Create and Manage Rides
* 📍 Add Route with Multiple Stops (via points)
* 🔎 Search Rides by Location (Landmark-based)
* 💰 Send Ride Requests with Offer Price
* 📩 Driver Dashboard to Accept/Reject Requests
* 📊 Real-time Ride & Request Management

---

## 🛠️ Tech Stack

* **Backend:** Python (Flask)
* **Frontend:** HTML, CSS
* **Database:** SQLite (carpool.db)
* **Deployment:** Render

---

## 📂 Project Structure

```
CollegeSaathi/
│── app.py
│── carpool.db
│── requirements.txt
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── create_ride.html
│   ├── update_ride.html
│   ├── search.html
│   └── driver_requests.html
│
├── static/
│   ├── style.css
│   └── assets/
```

---

## 🚀 Installation & Setup

### 1. Clone the repository

```
git clone https://github.com/your-username/CollegeSaathi.git
cd CollegeSaathi
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Run the app

```
python app.py
```

---

## 🌐 Deployment (Render)

* Add `gunicorn` in requirements.txt
* Start command:

```
gunicorn app:app
```

---

## ⚠️ Note

* SQLite database is used for simplicity
* For production, PostgreSQL is recommended

---

## 💡 Future Improvements

* 📱 Mobile responsiveness
* 📍 Google Maps integration
* 🔔 Notifications system
* 💳 Online payment integration

---

## 👨‍💻 Author

**Ronak Tamboli**
MLVTIAN 🚀

---

## ❤️ Acknowledgment

Made with passion to simplify daily commute for students.

---

## 📌 Tagline

> Built for MLVTIANS, by an MLVTIAN.
