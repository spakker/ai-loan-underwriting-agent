import os
from typing import Dict, Any, List
from langchain.docstore.document import Document
from backend.test_retrieval import run_retrieval_test
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
from langchain_core.tools import tool

# Define risk metric queries and their descriptions
RISK_METRIC_QUERIES = {
    "dti_ratio": {
        "query": "What are the front-end and back-end DTI ratio requirements for conventional mortgage loans? Include maximum thresholds, compensating factors, and any exceptions for FHA or VA loans.",
        "description": "Debt-to-Income (DTI) Ratio requirements including front-end housing ratio and back-end total debt ratio"
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
    
    # Get policy context for each metric
    dti_context = get_risk_policy_context("dti_ratio")
    ltv_context = get_risk_policy_context("ltv_ratio")
    credit_context = get_risk_policy_context("credit_score")
    down_payment_context = get_risk_policy_context("down_payment")
    
    # Compile results
    return {
        "calculated_metrics": {
            "dti_ratio": dti_ratio,
            "ltv_ratio": ltv_ratio,
            "down_payment_percent": down_payment_percent,
            "credit_score": loan_data["credit_score"]
        },
        "policy_context": {
            "dti_ratio": [doc.page_content for doc in dti_context],
            "ltv_ratio": [doc.page_content for doc in ltv_context],
            "credit_score": [doc.page_content for doc in credit_context],
            "down_payment": [doc.page_content for doc in down_payment_context]
        }
    } 