# 🚀 Rekapin FastAPI

Rekapin FastAPI is a backend service designed to handle **audio transcription and summarization** workflows.  
It integrates with **Supabase**, **Groq AI models**, and **Redis Queue (RQ)** for background processing.

---

## 📂 Project Structure

rekapin-fastapi/
├── app/
│ ├── main.py # FastAPI entry point
│ ├── routes/ # API routers
│ ├── services/ # External service integrations (Supabase, Groq, Redis, etc.)
│ ├── models/ # Pydantic schemas
│ ├── auth/ # Auth utilities
│ └── config/ # App configuration
├── worker/
│ └── summarize_worker.py # RQ worker for background summarization
├── docker-compose.yml # Multi-service setup (FastAPI, Redis, Worker)
├── requirements.txt # Python dependencies
└── README.md # Project documentation


---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash```
git clone https://github.com/<your-username>/rekapin-fastapi.git
cd rekapin-fastapi

###2️⃣ Create a Virtual Environment
python -m venv venv
source venv/bin/activate     # macOS/Linux
venv\Scripts\activate        # Windows

### 3️⃣ Install Dependencies
pip install -r requirements.txt

### 4️⃣ Configure Environment Variables

Create a .env file in the root directory:

SUPABASE_URL=<your_supabase_url>
SUPABASE_KEY=<your_supabase_key>
GROQ_API_KEY=<your_groq_api_key>
JWT_SECRET=<your_jwt_secret>
REDIS_URL=redis://redis:6379/0


🧩 Running the Project
🔹 Run with Docker
docker-compose up --build


This starts:

FastAPI backend (app)

Redis server

Worker process (worker/summarize_worker.py)

🔹 Run Locally (without Docker)

Start Redis manually, then run:

uvicorn app.main:app --reload


And in another terminal:

rq worker --with-scheduler


# 🧠 Key Features :
📝 Summarization using Groq LLM
🔐 Token-based authentication
🔄 Background task queue with Redis + RQ
☁️ Supabase integration for data persistence
