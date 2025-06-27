# Loan Underwriting Agent

This application provides mortgage risk analysis by processing financial documents using a FastAPI backend and Gradio frontend interface.

## 🛠️ Prerequisites

- Python 3.12
- pip (Python package installer)
- Virtual environment (recommended)

## 🚀 Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-loan-underwriting-agent
   ```

2. **Create and activate virtual environment**
   
   Windows:
   ```bash
   py -3.12 -m venv venv --upgrade-deps
   .\venv\Scripts\activate
   ```

   Linux/Mac:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   OPIK_API_KEY=your_opik_api_key_here
   OPIK_WORKSPACE=your_opik_workspace_here
   OPIK_PROJECT_NAME=your_opik_project_name_here
   ```

## 🏃‍♂️ Running the Application

1. **Start the Backend Server**
   
   Open a terminal and run:
   ```bash
   cd backend
   uvicorn main:app --reload
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
   - Financial Analysis: Shows financial ratios and risk assessment
   - Extracted Text: Displays the processed text from documents
   - Status: Indicates analysis progress and completion

## 🔍 Features

### Document Processing
- PDF document validation and text extraction
- Support for multiple document uploads
- Detailed text extraction preview

### Financial Analysis
- Automated data extraction using GPT-4
- Key financial metrics calculation:
  - Gross Debt-to-Income (DTI) Ratio
  - Back-End DTI Ratio
  - Loan-to-Value (LTV) Ratio
  - Credit Utilization Rate
  - Savings-to-Income Ratio
  - Net Worth-to-Income Ratio

### Risk Assessment
- Color-coded risk indicators (✅ Low Risk, ⚠️ High Risk)
- Automated risk profiling based on industry standards:
  - DTI ≤ 28%: Low Risk
  - Back-End DTI ≤ 36%: Low Risk
  - LTV ≤ 80%: Low Risk
  - Credit Utilization ≤ 30%: Low Risk
  - Savings ≥ 10% of Income: Good
  - Net Worth ≥ 50% of Income: Strong

### Error Handling
- Comprehensive PDF validation
- Detailed error messages
- Graceful failure handling

## ⚠️ Troubleshooting

- If the backend fails to start, ensure port 8000 is available
- If the frontend fails to start, ensure port 7860 is available
- Verify that your OpenAI API key is correctly set in the `.env` file
- Make sure all dependencies are installed correctly
- Check that uploaded files are in PDF format

## 📝 Notes

- The application requires a valid OpenAI API key for the GPT-4 integration
- Only PDF documents are supported
- Large PDF files may take longer to process
- The application uses industry-standard metrics for risk assessment
- All financial calculations are performed with proper validation to prevent errors 