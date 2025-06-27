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
   OPIK_WORKSPACE=your_workspace_name
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

## 📊 Setting Up Model Evaluation

The application includes a model evaluation system using Opik. Follow these steps to set up your evaluation environment:

### 1. Opik Account Setup
1. Sign up for an Opik account at [opik.ai](https://opik.ai)
2. Create a new workspace or use an existing one
3. Generate an API key from your workspace settings
4. Add the API key and workspace name to your `.env` file:
   ```
   OPIK_API_KEY=your_opik_api_key_here
   OPIK_WORKSPACE=your_workspace_name
   ```

### 2. Creating the Evaluation Dataset
1. Log into your Opik dashboard
2. Navigate to "Datasets" and click "Create New Dataset"
3. Name your dataset "loan_underwriting_eval"
4. Add evaluation samples in the following format:
   ```json
   {
     "input": "Sample loan application text...",
     "expected_output": {
       "risk_assessment": ["Risk factor 1", "Risk factor 2"],
       "decision_type": "Approve/Deny/Refer",
       "loan_decision_summary": "Detailed decision explanation"
     }
   }
   ```
5. Add at least 10-20 diverse samples covering different scenarios:
   - Clear approval cases
   - Clear denial cases
   - Edge cases requiring referral
   - Various risk combinations

### 3. Configuring Evaluation Metrics
The application uses three key metrics:
- **Hallucination**: Measures if the model makes unfounded claims
- **Answer Relevance**: Ensures responses are relevant to loan underwriting
- **Context Precision**: Verifies proper use of provided information

These metrics are automatically configured when you run the evaluation.

### 4. Running Evaluations
1. Start the application following the standard setup instructions
2. Navigate to the "Model Evaluation" tab in the UI
3. Click "Run Evaluation" to start the process
4. View results showing:
   - Individual metric scores
   - Progress bars for visual feedback
   - Overall experiment details

### 5. Best Practices
- Regularly update your evaluation dataset with new cases
- Include edge cases and challenging scenarios
- Monitor trends in model performance over time
- Use evaluation results to guide model improvements
- Document any specific patterns or issues discovered

### 6. Troubleshooting Evaluation Setup
- Verify your Opik API key and workspace are correctly set
- Ensure your dataset follows the required format
- Check that your dataset has sufficient samples
- Monitor the application logs for any evaluation errors
- Verify network connectivity to Opik services

For more information about Opik and advanced evaluation features, visit the [Opik Documentation](https://docs.opik.ai). 