# Loan Underwriting Agent

This application provides mortgage risk analysis by processing financial documents using a FastAPI backend and Gradio frontend interface.

## 🛠️ Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## 🚀 Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mortgage_risk_gradio_repo
   ```

2. **Create and activate virtual environment**
   
   Windows:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

   Linux/Mac:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## 🏃‍♂️ Running the Application

1. **Start the Backend Server**
   
   Open a terminal and run:
   ```bash
   cd backend
   python main.py
   ```
   The backend server will start at `http://localhost:8000`

2. **Start the Frontend Interface**
   
   Open another terminal and run:
   ```bash
   cd frontend
   python app.py
   ```
   The Gradio interface will be available at `http://localhost:7860`

## 📱 Using the Application

1. Open your web browser and navigate to `http://localhost:7860`
2. Upload PDF documents containing financial information
3. Click "Analyze Documents" to process the files
4. View results in three sections:
   - Upload Documents: For file upload and analysis initiation
   - Analysis Results: Shows financial ratios and risk assessment
   - Extracted Text: Displays the processed text from documents

## 🔍 Features

- PDF document processing and validation
- Financial data extraction using GPT-4
- Key financial metrics calculation (DTI, LTV, Credit Utilization)
- Risk assessment with color-coded indicators
- Detailed text extraction view
- Error handling and status indicators

## ⚠️ Troubleshooting

- If the backend fails to start, ensure port 8000 is available
- If the frontend fails to start, ensure port 7860 is available
- Verify that your OpenAI API key is correctly set in the `.env` file
- Make sure all dependencies are installed correctly
- Check that uploaded files are in PDF format

## 📝 Note

- The application requires a valid OpenAI API key for the GPT-4 integration
- Ensure uploaded documents are in PDF format
- Large PDF files may take longer to process 