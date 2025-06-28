import os
from typing import Dict, Any, List
from langchain.docstore.document import Document
from backend.rag_retrieval import run_retrieval_test
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
import re
from langchain_core.tools import tool

# Define risk metric queries and their descriptions
RISK_METRIC_QUERIES = {
    "dti_ratio": {
        "query": "What are the specific DTI ratio limits and thresholds for conventional mortgage loans? Please provide: 1) Maximum front-end DTI ratio (housing ratio) percentage, 2) Maximum back-end DTI ratio (total debt ratio) percentage, 3) Any compensating factors that allow higher DTI ratios, 4) Specific numerical ranges for different loan types (conventional, FHA, VA), 5) Minimum credit score requirements for different DTI levels, 6) Any exceptions or special programs. Include exact percentages and numerical thresholds.",
        "description": "Debt-to-Income (DTI) Ratio requirements including front-end housing ratio and back-end total debt ratio with specific numerical thresholds"
    },
    "dti_ratio_detailed": {
        "query": "Extract specific DTI ratio numbers and ranges from the mortgage guidelines. Find: front-end DTI maximum percentages, back-end DTI maximum percentages, qualifying ratios, compensating factor thresholds, credit score requirements for different DTI levels, and any exceptions. Provide exact numerical values and percentage ranges.",
        "description": "Detailed numerical DTI ratio requirements and thresholds for risk assessment"
    },
    "dti_ratio_by_credit": {
        "query": "What are the DTI ratio limits broken down by credit score tiers? Provide specific maximum DTI percentages for different FICO score ranges (e.g., 760+, 720-759, 680-719, etc.) and any compensating factors that allow higher ratios at each credit level.",
        "description": "DTI ratio limits by credit score tiers with specific numerical thresholds"
    },
    "ltv_ratio": {
        "query": "What are the LTV limits for conventional mortgage loans? Include requirements for primary residence, different property types, and PMI thresholds. Specify any differences for purchase vs refinance.",
        "description": "Loan-to-Value (LTV) Ratio limits for different mortgage types and scenarios"
    },
    "credit_score": {
        "query": "What are the minimum FICO score requirements for conventional mortgage loans? Include credit score tiers, pricing adjustments, and waiting periods after bankruptcy/foreclosure.",
        "description": "Credit score requirements, tiers, and history requirements for mortgage approval"
    },
    "down_payment": {
        "query": "What are the minimum down payment requirements for conventional mortgages? Include requirements for different property types, allowable sources of funds, and gift money policies.",
        "description": "Down payment requirements, acceptable sources, and documentation needs"
    },
    "income_verification": {
        "query": "What documentation is required to verify income for conventional mortgage loans? Include requirements for W-2 employees, self-employed borrowers, and other income types.",
        "description": "Income verification requirements and acceptable documentation types"
    },
    "property_eligibility": {
        "query": "What are the property eligibility requirements for conventional mortgages? Include property types, occupancy requirements, and appraisal standards.",
        "description": "Property eligibility criteria and appraisal requirements"
    },
    "mortgage_insurance": {
        "query": "What are the mortgage insurance requirements for conventional loans? Include LTV thresholds, coverage requirements, and options for removal.",
        "description": "Private Mortgage Insurance (PMI) requirements and guidelines"
    }
}

def get_risk_policy_context(metric_name: str, k: int = 3) -> List[Document]:
    """Retrieve relevant policy context for a specific risk metric."""
    if metric_name not in RISK_METRIC_QUERIES:
        raise ValueError(f"Unknown risk metric: {metric_name}. Must be one of {list(RISK_METRIC_QUERIES.keys())}")
    
    query = RISK_METRIC_QUERIES[metric_name]["query"]
    return run_retrieval_test(query, k=k)

def extract_dti_numerical_data(loan_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse numerical DTI data from policy documents for specific loan scenarios."""
    # Get detailed DTI context with multiple specialized queries
    dti_general = get_risk_policy_context("dti_ratio", k=5)
    dti_detailed = get_risk_policy_context("dti_ratio_detailed", k=5)
    dti_by_credit = get_risk_policy_context("dti_ratio_by_credit", k=5)
    
    # Calculate current DTI ratios
    dti_ratio = calculate_dti_ratio(loan_data["monthly_debt"], loan_data["monthly_income"])
    credit_score = loan_data["credit_score"]
    
    # Parse numerical data from all retrieved documents
    all_documents = dti_general + dti_detailed + dti_by_credit
    parsed_data = parse_numerical_dti_data(all_documents)
    
    # Determine applicable limits based on credit score
    applicable_limit = None
    for score_threshold in sorted(parsed_data["credit_tier_limits"].keys(), reverse=True):
        if credit_score >= score_threshold:
            applicable_limit = parsed_data["credit_tier_limits"][score_threshold]
            break
    
    # Create structured response with numerical data
    return {
        "current_dti": round(dti_ratio, 2),
        "credit_score": credit_score,
        "parsed_thresholds": parsed_data,
        "applicable_limit": applicable_limit,
        "policy_context": {
            "general_limits": [doc.page_content for doc in dti_general],
            "detailed_numbers": [doc.page_content for doc in dti_detailed],
            "credit_based_limits": [doc.page_content for doc in dti_by_credit]
        },
        "risk_assessment": {
            "dti_level": "high" if dti_ratio > 43 else "medium" if dti_ratio > 36 else "low",
            "credit_tier": "excellent" if credit_score >= 760 else "good" if credit_score >= 700 else "fair" if credit_score >= 650 else "poor",
            "within_limits": dti_ratio <= (applicable_limit or 43) if applicable_limit else None,
            "margin": round((applicable_limit or 43) - dti_ratio, 2) if applicable_limit else None
        }
    }

def calculate_dti_ratio(monthly_debt: float, monthly_income: float) -> float:
    """Calculate Debt-to-Income ratio."""
    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than 0")
    
    return (monthly_debt / monthly_income) * 100

def calculate_ltv_ratio(loan_amount: float, property_value: float) -> float:
    """Calculate Loan-to-Value ratio."""
    if property_value <= 0:
        raise ValueError("Property value must be greater than 0")
    
    return (loan_amount / property_value) * 100

def evaluate_risk_metrics(loan_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate risk metrics for a loan application and provide policy context."""
    # Validate required fields
    required_fields = ["monthly_debt", "monthly_income", "loan_amount", "property_value", "credit_score", "down_payment"]
    for field in required_fields:
        if field not in loan_data:
            raise ValueError(f"Missing required loan data field: {field}")
    
    # Calculate key ratios
    dti_ratio = calculate_dti_ratio(loan_data["monthly_debt"], loan_data["monthly_income"])
    ltv_ratio = calculate_ltv_ratio(loan_data["loan_amount"], loan_data["property_value"])
    down_payment_percent = (loan_data["down_payment"] / loan_data["property_value"]) * 100
    
    # Get optimized DTI analysis with numerical data
    dti_analysis = extract_dti_numerical_data(loan_data)
    
    # Get policy context for other metrics
    ltv_context = get_risk_policy_context("ltv_ratio")
    credit_context = get_risk_policy_context("credit_score")
    down_payment_context = get_risk_policy_context("down_payment")
    
    # Compile results
    return {
        "calculated_metrics": {
            "dti_ratio": round(dti_ratio, 2),
            "ltv_ratio": round(ltv_ratio, 2),
            "down_payment_percent": round(down_payment_percent, 2),
            "credit_score": loan_data["credit_score"]
        },
        "dti_analysis": dti_analysis,
        "policy_context": {
            "ltv_ratio": [doc.page_content for doc in ltv_context],
            "credit_score": [doc.page_content for doc in credit_context],
            "down_payment": [doc.page_content for doc in down_payment_context]
        }
    }

def parse_numerical_dti_data(documents: List[Document]) -> Dict[str, Any]:
    """Parse numerical DTI data from retrieved documents using regex and text analysis."""
    dti_data = {
        "front_end_limits": [],
        "back_end_limits": [],
        "credit_tier_limits": {},
        "compensating_factors": [],
        "exceptions": []
    }
    
    # Regex patterns to find numerical DTI data
    patterns = {
        "front_end": r"front[-\s]?end.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "back_end": r"back[-\s]?end.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "dti_general": r"DTI.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "housing_ratio": r"housing.*?ratio.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "total_debt": r"total.*?debt.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "credit_score_ranges": r"(\d{3})\+.*?(\d{1,2}(?:\.\d{1,2})?)%",
        "compensating": r"compensating.*?factor",
        "exception": r"exception|waiver|special"
    }
    
    for doc in documents:
        text = doc.page_content.lower()
        
        # Extract front-end limits
        front_matches = re.findall(patterns["front_end"], text, re.IGNORECASE)
        dti_data["front_end_limits"].extend([float(match) for match in front_matches])
        
        # Extract back-end limits
        back_matches = re.findall(patterns["back_end"], text, re.IGNORECASE)
        dti_data["back_end_limits"].extend([float(match) for match in back_matches])
        
        # Extract general DTI limits
        general_matches = re.findall(patterns["dti_general"], text, re.IGNORECASE)
        dti_data["back_end_limits"].extend([float(match) for match in general_matches])
        
        # Extract credit score based limits
        credit_matches = re.findall(patterns["credit_score_ranges"], text, re.IGNORECASE)
        for credit_score, dti_limit in credit_matches:
            dti_data["credit_tier_limits"][int(credit_score)] = float(dti_limit)
        
        # Check for compensating factors
        if re.search(patterns["compensating"], text, re.IGNORECASE):
            dti_data["compensating_factors"].append(doc.page_content)
        
        # Check for exceptions
        if re.search(patterns["exception"], text, re.IGNORECASE):
            dti_data["exceptions"].append(doc.page_content)
    
    # Remove duplicates and sort
    dti_data["front_end_limits"] = sorted(list(set(dti_data["front_end_limits"])))
    dti_data["back_end_limits"] = sorted(list(set(dti_data["back_end_limits"])))
    
    return dti_data

def test_optimized_dti_analysis():
    """Test the optimized DTI analysis with sample loan data."""
    sample_loan_data = {
        "monthly_debt": 2500,
        "monthly_income": 8000,
        "loan_amount": 300000,
        "property_value": 375000,
        "credit_score": 720,
        "down_payment": 75000
    }
    
    try:
        print("Testing optimized DTI analysis...")
        print(f"Sample loan data: {sample_loan_data}")
        
        # Test the optimized DTI analysis
        dti_analysis = extract_dti_numerical_data(sample_loan_data)
        
        print("\n=== DTI Analysis Results ===")
        print(f"Current DTI: {dti_analysis['current_dti']}%")
        print(f"Credit Score: {dti_analysis['credit_score']}")
        print(f"Credit Tier: {dti_analysis['risk_assessment']['credit_tier']}")
        print(f"DTI Level: {dti_analysis['risk_assessment']['dti_level']}")
        
        if dti_analysis['applicable_limit']:
            print(f"Applicable Limit: {dti_analysis['applicable_limit']}%")
            print(f"Within Limits: {dti_analysis['risk_assessment']['within_limits']}")
            print(f"Margin: {dti_analysis['risk_assessment']['margin']}%")
        
        print(f"\nParsed Thresholds:")
        print(f"Front-end limits: {dti_analysis['parsed_thresholds']['front_end_limits']}")
        print(f"Back-end limits: {dti_analysis['parsed_thresholds']['back_end_limits']}")
        print(f"Credit tier limits: {dti_analysis['parsed_thresholds']['credit_tier_limits']}")
        
        return dti_analysis
        
    except Exception as e:
        print(f"Error in DTI analysis: {str(e)}")
        return None

if __name__ == "__main__":
    test_optimized_dti_analysis() 