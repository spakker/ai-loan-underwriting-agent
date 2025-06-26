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
from pydantic import SecretStr

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

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

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
        
        # Create the LLM
        llm = ChatOpenAI(
            model="gpt-4", 
            api_key=SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else None,
            temperature=0
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
        
        # Run the chain
        try:
            data = chain.invoke(text)
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

def calculate_risk_metrics(data: Dict) -> Tuple[Dict, Dict]:
    """Calculate risk metrics from financial data"""
    try:
        # Calculate DTI (Debt-to-Income) ratio
        monthly_gross_income = data["gross_annual_income"] / 12
        dti = (data["monthly_housing_expense"] / monthly_gross_income * 100) if monthly_gross_income > 0 else 100.0
        
        # Calculate Back-End DTI
        back_end_dti = ((data["monthly_housing_expense"] + data["monthly_total_debt"]) / monthly_gross_income * 100) if monthly_gross_income > 0 else 100.0
        
        # Calculate LTV (Loan-to-Value) ratio
        ltv = (data["loan_amount"] / data["property_value"] * 100) if data["property_value"] > 0 else 100.0
        
        # Calculate Credit Utilization
        credit_utilization = (data["credit_used"] / data["credit_limit"] * 100) if data["credit_limit"] > 0 else 100.0
        
        # Calculate Savings to Income ratio
        savings_to_income = (data["savings"] / data["gross_annual_income"] * 100) if data["gross_annual_income"] > 0 else 0.0
        
        # Calculate Net Worth to Income ratio
        net_worth = data["savings"] - data["credit_used"] - data["loan_amount"]
        net_worth_to_income = (net_worth / data["gross_annual_income"] * 100) if data["gross_annual_income"] > 0 else 0.0
        
        ratios = {
            "DTI": round(dti, 1),
            "BackEndDTI": round(back_end_dti, 1),
            "LTV": round(ltv, 1),
            "CreditUtilization": round(credit_utilization, 1),
            "SavingsToIncome": round(savings_to_income, 1),
            "NetWorthToIncome": round(net_worth_to_income, 1)
        }
        
        # Create risk profile
        risk_profile = {
            "employment_title": "Not Available",
            "employer_name": "Not Available",
            "gross_annual_income": data["gross_annual_income"],
            "monthly_net_income": data["monthly_net_income"],
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
        
        return ratios, risk_profile
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {str(e)}", exc_info=True)
        # Return safe default values
        return {
            "DTI": 100.0,
            "BackEndDTI": 100.0,
            "LTV": 100.0,
            "CreditUtilization": 100.0,
            "SavingsToIncome": 0.0,
            "NetWorthToIncome": 0.0
        }, {
            "employment_title": "Not Available",
            "employer_name": "Not Available",
            "gross_annual_income": 0,
            "monthly_net_income": 0,
            "risk_flags": ["Unable to calculate risk metrics"]
        }

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
        
        # Calculate risk metrics
        ratios, risk_profile = calculate_risk_metrics(data)
        
        return {"ratios": ratios, "risk_profile": risk_profile}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze_complete endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
