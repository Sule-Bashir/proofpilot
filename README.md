# 📄 ProofPilot
Your expenses, handled. Your attention, protected.
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141%2B-green)](https://fastapi.tiangolo.com/)
ProofPilot is an AI agent that autonomously processes receipts and expense evidence. It extracts vendor, amount, and category from text, images, and PDFs using Strands Agents SDK and Groq AI. The agent auto-approves expenses with high confidence (>80%) and only asks for human review when uncertain.
## 🎯 The Problem
Freelancers, small-business owners, and NGO staff waste hours manually entering receipts into spreadsheets. ProofPilot automates this repetitive task, saving 5+ hours per week and reducing human error.
## 🤖 How It Works
1. Upload a receipt (text, image, or PDF)
2. AI extracts vendor, amount, category, and confidence
3. Auto-approves expenses with confidence >80%
4. Flags uncertain items for human review
5. Stores expenses in a searchable database
6. Provides real-time statistics and dashboard
## 🏆 Why It Matters
- Saves 5+ hours per week on expense tracking
- Reduces human error in bookkeeping
- Provides real-time expense visibility
- Scales from freelancers to small businesses
## 🛠️ Tech Stack
- Agent Framework: Strands Agents SDK
- AI Models: Groq API (`openai/gpt-oss-120b` for text, `qwen/qwen3.6-27b` for images)
- Backend: FastAPI + Python
- Frontend: HTML + CSS + JavaScript
- Database:SQLite
- Deployment:Render (backend) + Vercel (frontend)
## 📂 Project Structure
```
proofpilot/
├── app.py              # FastAPI backend with Strands Agent
├── index.html          # Web interface
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── LICENSE             # MIT License
├── render.yaml         # Render deployment config
├── vercel.json         # Vercel deployment config
└── expenses.db         # SQLite database (auto-generated)
```
## 🚀 Quick Start
### Prerequisites
- Python 3.10+
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Termux (Android) or any terminal
### Installation
```bash
# Clone the repository
git clone https://github.com/Sule-Bashir/proofpilot.git
cd proofpilot
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
# Set your Groq API key
export GROQ_API_KEY="your_gsk_key_here"
# Run the app
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
### Demo Files
- `receipt.txt` - Sample text receipt
- `simple_test.jpg` - Sample image receipt
- `Testing File.pdf` - Sample PDF receipt
## 🌐 Live Demo
- Frontend: [https://proofpilot-indol.vercel.app](https://proofpilot-indol.vercel.app)
- Backend API: [https://proofpilot-bpj6.onrender.com](https://proofpilot-bpj6.onrender.com)
- GitHub: [https://github.com/Sule-Bashir/proofpilot](https://github.com/Sule-Bashir/proofpilot)
## 📊 Architecture

```
User → Vercel Frontend → Render API → Strands Agent
                                       ↓
                          ┌────────────┼────────────┐
                          ↓            ↓            ↓
                     Extract    Validate    Duplicate Check
                          ↓            ↓            ↓
                          └────────────┼────────────┘
                                       ↓
                                Decision Engine
                                       ↓
                          ┌────────────┴────────────┐
                          ↓                         ↓
                     Auto-Approved           Needs Review
                          ↓                         ↓
                        SQLite               Human Decision
```
## 🧪 Testing
Upload a receipt through the web interface or use curl:
```bash
# Test with text receipt
curl -X POST -F "file=@receipt.txt" \
  https://proofpilot-bpj6.onrender.com/process-receipt
# Test with image receipt
curl -X POST -F "file=@simple_test.jpg" \
  https://proofpilot-bpj6.onrender.com/process-receipt
## 📝 License
MIT License - see the [LICENSE](LICENSE) file for details.
## 👤 Author
Sule Bashir
- GitHub: [@Sule-Bashir](https://github.com/Sule-Bashir)
- AWS Builder ID: @bashman
## 🙏 Acknowledgments
- Built for the Agents for Humans Hackathon
- Powered by Strands Agents SDK and Groq AI
- Hosted on Render and Vercel
## 📧 Contact
For questions or feedback, please open an issue on GitHub.
Built with ❤️ on Android using Termux
