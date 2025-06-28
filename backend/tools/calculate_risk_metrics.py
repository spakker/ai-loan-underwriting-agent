import os
import logging
from typing import Dict, Any, List
from langchain.docstore.document import Document
from rag.test_retrieval import run_retrieval_test

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Define risk metric queries and their descriptions
RISK_METRIC_QUERIES = {
    "dti_ratio": {
        "query": "What are the requirements and limits for debt-to-income ratio?",
        "description": "Debt-to-Income (DTI) Ratio requirements and thresholds"
    },
    "ltv_ratio": {
        "query": "What are the requirements and limits for loan-to-value ratio?",
        "description": "Loan-to-Value (LTV) Ratio requirements and thresholds"
    },
    "credit_score": {
        "query": "What are the minimum credit score requirements?",
        "description": "Minimum credit score requirements and thresholds"
    },
    "down_payment": {
        "query": "What are the down payment requirements and minimums?",
        "description": "Down payment requirements and minimum thresholds"
    },
    "income_verification": {
        "query": "What are the income verification and documentation requirements?",
        "description": "Income verification and documentation requirements"
    }
}

def get_risk_policy_context(metric_name: str, k: int = 3) -> List[Document]:
    """Retrieve relevant policy context for a specific risk metric.
    
    Args:
        metric_name (str): Name of the risk metric (must be in RISK_METRIC_QUERIES)
        k (int, optional): Number of relevant documents to retrieve. Defaults to 3.
    
    Returns:
        List[Document]: List of relevant policy documents
    """
    if metric_name not in RISK_METRIC_QUERIES:
        raise ValueError(f"Unknown risk metric: {metric_name}. Must be one of {list(RISK_METRIC_QUERIES.keys())}")
    
    query = RISK_METRIC_QUERIES[metric_name]["query"]
    logger.info(f"Retrieving policy context for {metric_name}")
    return run_retrieval_test(query, k=k)

def calculate_dti_ratio(monthly_debt: float, monthly_income: float) -> float:
    """Calculate Debt-to-Income ratio.
    
    Args:
        monthly_debt (float): Total monthly debt payments
        monthly_income (float): Total monthly income
    
    Returns:
        float: DTI ratio as a percentage
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than 0")
    return (monthly_debt / monthly_income) * 100

def calculate_ltv_ratio(loan_amount: float, property_value: float) -> float:
    """Calculate Loan-to-Value ratio.
    
    Args:
        loan_amount (float): Total loan amount requested
        property_value (float): Appraised property value
    
    Returns:
        float: LTV ratio as a percentage
    """
    if property_value <= 0:
        raise ValueError("Property value must be greater than 0")
    return (loan_amount / property_value) * 100

def evaluate_risk_metrics(loan_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate risk metrics for a loan application and provide policy context.
    
    Args:
        loan_data (Dict[str, Any]): Dictionary containing loan application data:
            - monthly_debt: Total monthly debt payments
            - monthly_income: Total monthly income
            - loan_amount: Total loan amount requested
            - property_value: Appraised property value
            - credit_score: Applicant's credit score
            - down_payment: Down payment amount
    
    Returns:
        Dict[str, Any]: Dictionary containing:
            - calculated metrics
            - policy requirements
            - compliance status
    """
    try:
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
        results = {
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
        
        logger.info("Risk metrics evaluation completed")
        return results
        
    except KeyError as e:
        raise ValueError(f"Missing required loan data field: {str(e)}")
    except Exception as e:
        logger.error(f"Error evaluating risk metrics: {str(e)}", exc_info=True)
        raise

def main():
    # Example usage
    sample_loan_data = {
        "monthly_debt": 2000,
        "monthly_income": 6000,
        "loan_amount": 300000,
        "property_value": 375000,
        "credit_score": 720,
        "down_payment": 75000
    }
    
    try:
        results = evaluate_risk_metrics(sample_loan_data)
        
        # Print results
        print("\nCalculated Metrics:")
        for metric, value in results["calculated_metrics"].items():
            print(f"{metric}: {value:.2f}")
        
        print("\nPolicy Requirements:")
        for metric, contexts in results["policy_context"].items():
            print(f"\n{metric} policies:")
            for i, context in enumerate(contexts, 1):
                print(f"{i}. {context[:200]}...")
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main() 