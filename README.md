# uzhavan-unavu
AI assistant to help farmers find the best market prices.
# 🌾 Uzhavan Unavu (Farmer's Link)

**An AI-powered friend that helps farmers find the best market price for their produce.**

*Project for the OpenAI & NxtWave Buildathon, submitted by Karthikadivi.*

---

## 🎯 The Problem

Small-hold farmers in India, particularly in regions like Madurai, often lack access to real-time market intelligence. This forces them to sell perishable goods, such as jasmine flowers, to local middlemen at low prices, significantly reducing their potential income. They have no easy way to compare prices from nearby city markets or understand the net profit after factoring in logistics costs. This information asymmetry is a major barrier to their economic growth.

## ✨ Our Solution

**Uzhavan Unavu** is a simple, AI-powered web application that acts as a personal agricultural advisor. Using a conversational interface in their native language (Tamil), a farmer can ask a question like, "I have 50kg of jasmine in Madurai, where can I get the best price tomorrow?". 

Our solution, built with Python and Streamlit, sends this query along with market data to Google's Gemini AI. The AI analyzes the data, calculates potential revenue and logistics costs for each market, and generates a clear, actionable recommendation with a profit comparison table. This empowers the farmer to make data-driven decisions instantly.

---

## 🛠️ Tech Stack

* **Frontend:** Streamlit
* **Backend:** Python
* **AI Model:** Google Gemini API (`models/gemini-2.5-flash`)
* **Key Libraries:** `streamlit`, `google-generativeai`

---

## 🚀 How to Run This Project

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Karthikadivi/uzhavan-unavu.git](https://github.com/Karthikadivi/uzhavan-unavu.git)
    cd uzhavan-unavu
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Add your API Key:**
    * Create a folder named `.streamlit`.
    * Inside it, create a file named `secrets.toml`.
    * Add your Google API Key to this file: `GOOGLE_API_KEY = "YOUR_API_KEY_HERE"`

5.  **Run the app:**
    ```bash
    streamlit run app.py
    ```
