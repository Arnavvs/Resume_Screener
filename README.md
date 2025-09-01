# 🤖 AI-Powered Resume Screening Application

An intelligent tool that automates and enhances the resume screening process using **Google’s Gemini Pro LLM** via **LangChain**.  
It analyzes, scores, and ranks resumes against a job description, with deep insights into candidate fit.

---

## ✨ Features
- 📂 **Batch Processing** – Upload & screen multiple resumes at once  
- 📊 **Dynamic Scoring** – Evaluate resumes across skills, experience, and fit  
- ⚖️ **Adjustable Strictness** – From lenient to very strict screening  
- 🔎 **In-Depth Analysis**  
  - 🚨 Red Flag Detection (job hopping, gaps, etc.)  
  - 💰 Salary Estimation (India market)  
  - ✅ Consistency Check (background verification)  
  - 🎯 Culture & Role Fit scoring  
- 🏆 **Top Candidate Recommendations** – Ranked list with justifications  

---

## 🛠 Tech Stack
- **Backend**: Flask, Python  
- **Frontend**: Streamlit  
- **AI/LLM**: Google Gemini Pro + LangChain  
- **PDF Processing**: pdfplumber  
- **Validation**: pydantic  

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+  
- Google Generative AI API Key (get from [Google AI Studio](https://makersuite.google.com/))

### 2. Setup
```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME

# Create venv
python -m venv venv
# Activate (Windows)
.\venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure
Create `.env` in the root directory:
```bash
GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

### 4. Run
Open **two terminals** (venv activated in both):

**Backend (Flask API):**
```bash
python app.py
```

**Frontend (Streamlit UI):**
```bash
streamlit run streamlit_dashboard.py
```

- Flask runs on: `http://127.0.0.1:5000`  
- Streamlit dashboard: `http://localhost:8501`  

---

## 📂 Project Structure
```
├── app.py                 # Flask backend
├── streamlit_dashboard.py # Streamlit frontend
├── resume_filter.py       # Resume analysis & LLM calls
├── requirements.txt       # Dependencies
├── .env                   # API key (user-created)
└── README.md              # Project docs
```

---

## 📜 License
Licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.

