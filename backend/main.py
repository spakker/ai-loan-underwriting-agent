from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Tuple
import json
import io
import PyPDF2
import logging
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic import SecretStr
from datetime import datetime
from opik.integrations.langchain import OpikTracer
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import Hallucination, AnswerRelevance, ContextPrecision
import sys

# Initialize Opik client for evaluations
opik_client = Opik()

def setup_evaluation():
    """Set up evaluation dataset and metrics"""
    try:
        # Get the evaluation dataset
        dataset = opik_client.get_dataset(name="loan_underwriting_eval")
        
        # Define evaluation metrics
        metrics = [
            Hallucination(),
            AnswerRelevance(),
            ContextPrecision()
        ]
        
        return dataset, metrics
    except Exception as e:
        logger.error(f"Error setting up evaluation: {str(e)}")
        return None, None

def evaluation_task(dataset_item):
    """Evaluation task for loan underwriting analysis"""
    try:
        # Extract input from dataset item
        input_text = dataset_item.get('input', '')
        expected_output = dataset_item.get('expected_output', {})
        
        # Run the loan analysis
        llm_result = analyze_with_llm(input_text)
        
        # Format result for evaluation
        result = {
            "input": input_text,
            "output": json.dumps(llm_result),
            "context": [input_text],  # Include any relevant context
            "expected_output": json.dumps(expected_output)
        }
        
        return result
    except Exception as e:
        logger.error(f"Error in evaluation task: {str(e)}")
        # Return a result indicating the error instead of None
        return {
            "input": dataset_item.get('input', ''),
            "output": json.dumps({"error": str(e)}),
            "context": [dataset_item.get('input', '')],
            "expected_output": json.dumps(dataset_item.get('expected_output', {}))
        }

def run_evaluation(experiment_name: str = "loan_underwriting_eval"):
    """Run evaluation on the loan underwriting system"""
    try:
        dataset, metrics = setup_evaluation()
        if not dataset or not metrics:
            logger.error("Failed to set up evaluation")
            return None
            
        eval_results = evaluate(
            experiment_name=experiment_name,
            dataset=dataset,
            task=evaluation_task,
            scoring_metrics=metrics
        )
        
        logger.info(f"Evaluation results: {eval_results}")
        return eval_results
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}")
        return None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Check for required API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPIK_API_KEY = os.getenv('OPIK_API_KEY')
OPIK_WORKSPACE = os.getenv('OPIK_WORKSPACE')
OPIK_PROJECT_NAME=os.getenv('OPIK_PROJECT_NAME')

# Log OPIK configuration
logger.info(f"OPIK Workspace: {OPIK_WORKSPACE}")
logger.info(f"OPIK Project Name: {OPIK_PROJECT_NAME}")

if not OPENAI_API_KEY:
    logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

if not OPIK_API_KEY or not OPIK_WORKSPACE:
    logger.error("Opik configuration not found. Please set OPIK_API_KEY and OPIK_WORKSPACE environment variables.")
    raise ValueError("Opik configuration not found. Please set OPIK_API_KEY and OPIK_WORKSPACE environment variables.")

# Configure Opik
os.environ["OPIK_API_KEY"] = OPIK_API_KEY
os.environ["OPIK_WORKSPACE"] = OPIK_WORKSPACE

# Initialize Opik tracer
opik_tracer = OpikTracer()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def inspect_file_content(content: bytes, filename: str) -> None:
    """Debug function to inspect file content"""
    try:
        logger.info(f"File {filename} content inspection:")
        hex_content = ' '.join([f'{b:02x}' for b in content[:20]])
        ascii_content = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in content[:20]])
        logger.info(f"First 20 bytes (hex): {hex_content}")
        logger.info(f"First 20 bytes (ascii): {ascii_content}")
        logger.info(f"Total content length: {len(content)} bytes")
    except Exception as e:
        logger.error(f"Error inspecting file content: {str(e)}")

def validate_pdf(file_obj: io.BytesIO) -> Tuple[bool, str]:
    """Validate if the PDF file is properly formatted and not corrupted"""
    try:
        file_obj.seek(0)
        header = file_obj.read(5)
        
        hex_header = ' '.join([f'{b:02x}' for b in header])
        ascii_header = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in header])
        logger.info(f"PDF header (hex): {hex_header}")
        logger.info(f"PDF header (ascii): {ascii_header}")
        
        if header != b'%PDF-':
            logger.error(f"Invalid PDF header signature. Expected '%PDF-', got: {ascii_header}")
            return False, f"Invalid PDF header - got '{ascii_header}' instead of '%PDF-'"
            
        file_obj.seek(0)
        try:
            reader = PyPDF2.PdfReader(file_obj, strict=False)
            num_pages = len(reader.pages)
            logger.info(f"PDF validation successful: {num_pages} pages found")
            return True, ""
        except Exception as pdf_error:
            logger.error(f"PyPDF2 validation error: {str(pdf_error)}")
            
            try:
                file_obj.seek(-1024, 2)
                footer = file_obj.read().lower()
                if b'%%eof' in footer or b'%%EOF' in footer:
                    logger.info("Found EOF marker in lenient check")
                    return True, ""
                else:
                    return False, "PDF appears to be incomplete (no EOF marker found)"
            except Exception as e:
                logger.error(f"EOF check error: {str(e)}")
                return False, f"Unable to validate PDF structure: {str(e)}"
    except Exception as e:
        logger.error(f"Error validating PDF: {str(e)}")
        return False, f"Error validating PDF: {str(e)}"

def extract_text_from_pdf(file_obj: io.BytesIO, filename: str) -> str:
    """Extract text from a PDF file"""
    try:
        reader = PyPDF2.PdfReader(file_obj, strict=False)
        logger.info(f"Successfully created PDF reader for {filename}")
        
        if len(reader.pages) == 0:
            logger.error(f"PDF {filename} has no pages")
            raise ValueError(f"The PDF file {filename} appears to be empty (no pages found)")
        
        text = ""
        for page_num, page in enumerate(reader.pages):
            try:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                logger.info(f"Extracted {len(extracted) if extracted else 0} characters from page {page_num + 1}")
            except Exception as e:
                logger.error(f"Error extracting text from page {page_num + 1}: {str(e)}", exc_info=True)
                raise ValueError(f"Error processing page {page_num + 1}: {str(e)}")
        
        if not text.strip():
            logger.error(f"No text extracted from {filename}")
            raise ValueError(f"No text could be extracted from {filename}. The PDF might be scanned or contain only images.")
        
        logger.info(f"Successfully extracted {len(text)} characters from {filename}")
        return text
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Error in text extraction: {str(e)}", exc_info=True)
        raise ValueError(f"Error extracting text: {str(e)}")

def process_files(files: List[UploadFile]) -> List[str]:
    """Process uploaded files and extract text"""
    all_text = []
    
    for file in files:
        logger.info(f"Processing file: {file.filename}")
        
        if not file.filename:
            logger.error("Received file with no filename")
            raise HTTPException(status_code=400, detail="File has no filename")
            
        if not file.filename.lower().endswith('.pdf'):
            logger.error(f"Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail=f"Invalid file type. Expected PDF, got: {file.filename}")
        
        try:
            content = file.file.read()  # Read from file.file instead of calling file.read()
            logger.info(f"Read {len(content)} bytes from {file.filename}")
            
            inspect_file_content(content, file.filename)
            
            if not content:
                logger.error(f"Received empty file content for {file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail=f"The file {file.filename} appears to be empty. Please check the file and try again."
                )
            
            file_obj = io.BytesIO(content)
            file_obj.name = file.filename
            
            is_valid, error_message = validate_pdf(file_obj)
            if not is_valid:
                raise HTTPException(
                    status_code=400, 
                    detail=f"The file {file.filename} validation failed: {error_message}. Please ensure the file is complete and try uploading again."
                )
            
            text = extract_text_from_pdf(file_obj, file.filename)
            all_text.append(text)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Error processing {file.filename}: {str(e)}")
    
    return all_text

def validate_financial_data(data: Dict) -> Dict:
    """Validate and clean financial data"""
    required_fields = [
        'gross_annual_income',
        'monthly_net_income',
        'monthly_housing_expense',
        'monthly_total_debt',
        'savings',
        'credit_used',
        'credit_limit',
        'loan_amount',
        'property_value'
    ]
    
    # Check for missing fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Ensure all values are numeric and non-negative
    cleaned_data = {}
    for field in required_fields:
        value = data.get(field)
        if value is None:
            raise ValueError(f"Field '{field}' has no value")
        try:
            numeric_value = float(value)
            if numeric_value < 0:
                raise ValueError(f"Field '{field}' cannot be negative")
            cleaned_data[field] = numeric_value
        except (TypeError, ValueError):
            raise ValueError(f"Field '{field}' must be a valid number, got: {value}")
    
    return cleaned_data

def analyze_with_llm(text: str) -> Dict:
    """Analyze text with LLM and calculate financial metrics"""
    try:
        logger.info("Starting LLM analysis")
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_template("""
You are a mortgage underwriting specialist extracting financial data for home loan approval.  

DOCUMENT TEXT:
{text}

EXTRACTION RULES:
Extract the following 11 values as numbers or text (as specified):
1. employment_title: Borrower's job title or occupation (e.g., Software Engineer, Nurse, Manager)
2. employer_name: Name of the borrower's current employer or company
3. gross_annual_income: Borrower total annual income BEFORE taxes (multiply bi-weekly pay by 26 or monthly by 12)
4. monthly_net_income: Monthly take-home pay AFTER taxes and deductions
5. monthly_housing_expense: NEW mortgage payment including Principal, Interest, Taxes, Insurance, PMI (NOT current rent)
6. monthly_total_debt: ALL monthly debt payments (new mortgage + credit cards + student loans + car loans)
7. savings: Total liquid assets available (checking + savings account balances)
8. credit_used: Current total credit card balances owed
9. credit_limit: Total credit card limits available
10. loan_amount: Requested mortgage loan amount (purchase price minus down payment)
11. property_value: Property purchase price or appraised value

CRITICAL INSTRUCTIONS:
- Use GROSS annual income (before taxes) for income calculations
- Use NEW mortgage payment (Principal+Interest+Taxes+Insurance+PMI) NOT current rent for housing_expense
- Include ALL debt payments (mortgage + existing debt) for monthly_total_debt
- If bi-weekly pay is given, multiply by 26 for annual income
- If property details show "Total Monthly Housing Payment" or "PITI", use that number
- Look for mortgage calculations like "Principal & Interest: $X" plus taxes and insurance

CALCULATION EXAMPLES:
- If bi-weekly gross pay = $3,170 → gross_annual_income = 82420 (3170 × 26)
- If new mortgage payment = $3,021 + taxes $506 + insurance $162 + PMI $307 → monthly_housing_expense = 3996
- If new housing payment = $3,996 AND existing debt = $836 → monthly_total_debt = 4832

VALIDATION CHECKS:
- monthly_housing_expense should be MUCH HIGHER than current rent (new mortgage vs old rent)
- monthly_total_debt should include monthly_housing_expense plus other debt
- gross_annual_income should be 12-15x monthly_net_income (due to taxes)

Return ONLY the JSON object with these exact field names:

{{
  "employment_title": "[text]",
  "employer_name": "[text]",
  "gross_annual_income": [number],
  "monthly_net_income": [number],
  "monthly_housing_expense": [number],
  "monthly_total_debt": [number],
  "savings": [number],
  "credit_used": [number],
  "credit_limit": [number],
  "loan_amount": [number],
  "property_value": [number]
}}

NO explanations, NO additional text, ONLY the JSON object.
""")
        
        # Create the LLM with Opik tracer
        llm = ChatOpenAI(
            model="gpt-4", 
            api_key=SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else None,
            temperature=0,
            callbacks=[opik_tracer]
        )
        
        # Create the parser
        parser = JsonOutputParser()
        
        # Create the chain
        chain = (
            {"text": RunnablePassthrough()} 
            | prompt 
            | llm 
            | parser
        )
        
        # Run the chain with Opik tracer
        try:
            data = chain.invoke(text, callbacks=[opik_tracer])
            logger.info("Successfully completed LLM analysis")
            
            # Validate and clean the data
            validated_data = validate_financial_data(data)
            logger.info("Successfully validated financial data")
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Error in LLM chain execution: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing text with LLM: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in LLM analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in AI analysis: {str(e)}")

class FinancialData(BaseModel):
    """Pydantic model for financial data validation"""
    gross_annual_income: float
    monthly_net_income: float
    monthly_housing_expense: float
    monthly_total_debt: float
    savings: float
    credit_used: float
    credit_limit: float
    loan_amount: float
    property_value: float
    employment_title: str = "Not Available"
    employer_name: str = "Not Available"
    
    class Config:
        extra = "allow"  # Allow additional fields

@tool
def calculate_risk_metrics(data: Dict) -> Dict:
    """Calculate comprehensive risk metrics for mortgage underwriting.
    
    This tool analyzes financial data to calculate key ratios and identify risk factors:
    - DTI (Debt-to-Income): Monthly housing expense as % of gross monthly income
    - Back-End DTI: Total monthly debt as % of gross monthly income  
    - LTV (Loan-to-Value): Loan amount as % of property value
    - Credit Utilization: Credit card balances as % of available credit
    - Savings to Income: Savings as % of annual income
    - Net Worth to Income: Net worth as % of annual income
    
    The tool automatically handles null/missing values and provides risk flags based on industry standards.
    
    Args:
        data: Dictionary containing financial data with fields:
            - gross_annual_income: Annual income before taxes
            - monthly_net_income: Monthly take-home pay after taxes
            - monthly_housing_expense: New mortgage payment including PITI
            - monthly_total_debt: All monthly debt payments
            - savings: Total liquid assets available
            - credit_used: Current total credit card balances
            - credit_limit: Total credit card limits available
            - loan_amount: Requested mortgage loan amount
            - property_value: Property purchase price or appraised value
            - employment_title: Borrower's job title (optional)
            - employer_name: Borrower's employer (optional)
    
    Returns:
        Dictionary containing:
        - ratios: Calculated financial ratios (DTI, LTV, etc.)
        - risk_profile: Borrower information and risk flags
    """
    print("Calculating risk metrics", data)
    
    try:
        # Clean and validate input data
        cleaned_data = clean_financial_data(data)
        
        # Validate input data to prevent impossible calculations
        if cleaned_data["gross_annual_income"] <= 0:
            raise ValueError("Gross annual income must be positive")
        if cleaned_data["property_value"] <= 0:
            raise ValueError("Property value must be positive")
        if cleaned_data["loan_amount"] < 0:
            raise ValueError("Loan amount cannot be negative")
        if cleaned_data["credit_limit"] < 0:
            raise ValueError("Credit limit cannot be negative")
        if cleaned_data["credit_used"] < 0:
            raise ValueError("Credit used cannot be negative")
        if cleaned_data["monthly_housing_expense"] < 0:
            raise ValueError("Monthly housing expense cannot be negative")
        if cleaned_data["monthly_total_debt"] < 0:
            raise ValueError("Monthly total debt cannot be negative")
        if cleaned_data["savings"] < 0:
            raise ValueError("Savings cannot be negative")
        
        # Calculate DTI (Debt-to-Income) ratio
        monthly_gross_income = cleaned_data["gross_annual_income"] / 12
        dti = (cleaned_data["monthly_housing_expense"] / monthly_gross_income * 100) if monthly_gross_income > 0 else 100.0
        
        # Validate DTI is reasonable (should not exceed 100% for housing alone)
        if dti > 100:
            logger.warning(f"DTI ratio calculated as {dti:.1f}% - capping at 100%")
            dti = 100.0
        
        # Calculate Back-End DTI
        back_end_dti = ((cleaned_data["monthly_housing_expense"] + cleaned_data["monthly_total_debt"]) / monthly_gross_income * 100) if monthly_gross_income > 0 else 100.0
        
        # Validate Back-End DTI is reasonable
        if back_end_dti > 100:
            logger.warning(f"Back-End DTI calculated as {back_end_dti:.1f}% - capping at 100%")
            back_end_dti = 100.0
        
        # Calculate LTV (Loan-to-Value) ratio
        ltv = (cleaned_data["loan_amount"] / cleaned_data["property_value"] * 100) if cleaned_data["property_value"] > 0 else 100.0
        
        # Validate LTV is reasonable (should not exceed 100%)
        if ltv > 100:
            logger.warning(f"LTV ratio calculated as {ltv:.1f}% - capping at 100%")
            ltv = 100.0
        
        # Calculate Credit Utilization (handle zero credit limit case)
        if cleaned_data["credit_limit"] == 0:
            credit_utilization = 0.0  # No credit limit means no utilization
        else:
            credit_utilization = (cleaned_data["credit_used"] / cleaned_data["credit_limit"] * 100)
            # Validate credit utilization is reasonable
            if credit_utilization > 100:
                logger.warning(f"Credit utilization calculated as {credit_utilization:.1f}% - capping at 100%")
                credit_utilization = 100.0
        
        # Calculate Savings to Income ratio
        savings_to_income = (cleaned_data["savings"] / cleaned_data["gross_annual_income"] * 100) if cleaned_data["gross_annual_income"] > 0 else 0.0
        
        # Calculate Net Worth to Income ratio
        net_worth = cleaned_data["savings"] - cleaned_data["credit_used"] - cleaned_data["loan_amount"]
        net_worth_to_income = (net_worth / cleaned_data["gross_annual_income"] * 100) if cleaned_data["gross_annual_income"] > 0 else 0.0
        
        # Validate ratios are finite numbers
        ratios = {
            "DTI": round(max(0, min(100, dti)), 1),
            "BackEndDTI": round(max(0, min(100, back_end_dti)), 1),
            "LTV": round(max(0, min(100, ltv)), 1),
            "CreditUtilization": round(max(0, min(100, credit_utilization)), 1),
            "SavingsToIncome": round(max(-100, min(1000, savings_to_income)), 1),  # Allow negative but cap at reasonable values
            "NetWorthToIncome": round(max(-1000, min(1000, net_worth_to_income)), 1)  # Allow negative but cap at reasonable values
        }
        
        # Create risk profile
        risk_profile = {
            "employment_title": cleaned_data.get("employment_title", "Not Available"),
            "employer_name": cleaned_data.get("employer_name", "Not Available"),
            "gross_annual_income": cleaned_data["gross_annual_income"],
            "monthly_net_income": cleaned_data["monthly_net_income"],
            "risk_flags": []
        }
        
        # Add risk flags based on standard thresholds
        if dti > 43:
            risk_profile["risk_flags"].append(f"DTI ratio ({dti:.1f}%) exceeds maximum threshold of 43%")
        if back_end_dti > 36:
            risk_profile["risk_flags"].append(f"Back-End DTI ({back_end_dti:.1f}%) exceeds recommended maximum of 36%")
        if ltv > 80:
            risk_profile["risk_flags"].append(f"LTV ratio ({ltv:.1f}%) exceeds standard maximum of 80%")
        if credit_utilization > 30:
            risk_profile["risk_flags"].append(f"Credit utilization ({credit_utilization:.1f}%) exceeds recommended 30%")
        if savings_to_income < 10:
            risk_profile["risk_flags"].append(f"Low savings relative to income ({savings_to_income:.1f}%)")
        if net_worth_to_income < 0:
            risk_profile["risk_flags"].append("Negative net worth relative to income")
        
        # Return combined result as a single dictionary
        return {
            "ratios": ratios,
            "risk_profile": risk_profile
        }
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {str(e)}", exc_info=True)
        # Return safe default values
        return {
            "ratios": {
                "DTI": 100.0,
                "BackEndDTI": 100.0,
                "LTV": 100.0,
                "CreditUtilization": 100.0,
                "SavingsToIncome": 0.0,
                "NetWorthToIncome": 0.0
            },
            "risk_profile": {
                "employment_title": "Not Available",
                "employer_name": "Not Available",
                "gross_annual_income": 0,
                "monthly_net_income": 0,
                "risk_flags": [f"Unable to calculate risk metrics: {str(e)}"]
            }
        }

def clean_financial_data(data: Dict) -> Dict:
    """Clean and validate financial data, handling null/missing values"""
    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary")
    
    # Define required fields and their default values
    required_fields = {
        "gross_annual_income": 0,
        "monthly_net_income": 0,
        "monthly_housing_expense": 0,
        "monthly_total_debt": 0,
        "savings": 0,
        "credit_used": 0,
        "credit_limit": 0,
        "loan_amount": 0,
        "property_value": 0
    }
    
    # Optional fields
    optional_fields = {
        "employment_title": "Not Available",
        "employer_name": "Not Available"
    }
    
    cleaned_data = {}
    
    # Process required fields
    for field, default_value in required_fields.items():
        value = data.get(field)
        
        # Handle null, None, empty string, or missing values
        if value is None or value == "" or value == "null" or value == "None":
            cleaned_data[field] = default_value
            logger.warning(f"Field '{field}' was null/missing, using default value: {default_value}")
        else:
            try:
                # Convert to float and validate
                float_value = float(value)
                if float_value < 0 and field not in ["credit_used", "loan_amount"]:
                    logger.warning(f"Field '{field}' was negative ({float_value}), using default value: {default_value}")
                    cleaned_data[field] = default_value
                else:
                    cleaned_data[field] = float_value
            except (ValueError, TypeError):
                logger.warning(f"Field '{field}' could not be converted to number ({value}), using default value: {default_value}")
                cleaned_data[field] = default_value
    
    # Process optional fields
    for field, default_value in optional_fields.items():
        value = data.get(field)
        if value is None or value == "" or value == "null" or value == "None":
            cleaned_data[field] = default_value
        else:
            cleaned_data[field] = str(value)
    
    logger.info(f"Cleaned data: {cleaned_data}")
    return cleaned_data

@app.post("/analyze")
async def analyze(files: List[UploadFile] = File(...)):
    """Main endpoint for analyzing financial documents"""
    try:
        # Extract text from all files
        all_text = process_files(files)
        
        # Prepare text extraction summary
        text_summary = []
        total_chars = 0
        for idx, text in enumerate(all_text):
            char_count = len(text)
            total_chars += char_count
            text_preview = text[:500] + "..." if len(text) > 500 else text
            text_summary.append({
                "file_name": files[idx].filename,
                "characters": char_count,
                "preview": text_preview
            })
            
        combined_text = "\n".join(all_text)
        logger.info(f"Combined text length: {len(combined_text)} characters")
        
        # Return text extraction results first
        return {
            "status": "text_extracted",
            "text_summary": {
                "total_characters": total_chars,
                "files": text_summary
            }
        }
        
        # The following code will be called in a separate endpoint
        # # Analyze text with LLM
        # data = analyze_with_llm(combined_text)
        
        # # Calculate risk metrics
        # ratios, risk_profile = calculate_risk_metrics(data)
        
        # return {"ratios": ratios, "risk_profile": risk_profile}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/analyze/complete")
async def analyze_complete(files: List[UploadFile] = File(...)):
    """Complete analysis endpoint including LLM processing"""
    try:
        # Extract text from all files
        all_text = process_files(files)
        combined_text = "\n".join(all_text)
        
        # Analyze text with LLM
        data = analyze_with_llm(combined_text)
        
        # Calculate risk metrics using the tool
        result = calculate_risk_metrics.invoke({"data": data})
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze_complete endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/evaluate")
async def evaluate_model():
    """Endpoint to run evaluation on the loan underwriting model"""
    try:
        eval_results = run_evaluation()
        if eval_results is None:
            raise HTTPException(status_code=500, detail="Evaluation failed")
        return eval_results
    except Exception as e:
        logger.error(f"Error in evaluation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
