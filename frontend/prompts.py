from langchain.prompts import ChatPromptTemplate

borrower_summary_prompt = ChatPromptTemplate.from_template("""
You are a loan underwriting assistant. Based on the borrower's information, provide a concise summary of their financial profile.
Focus on key aspects that are relevant for loan underwriting.

Information:
- Employment: {employment}
- Annual Income: {annual_income}
- Monthly Debt: {monthly_debt}
- DTI: {dti}%
- DSCR: {dscr}
- LTV: {ltv}%

Write a professional summary in 2-3 sentences that highlights:
1. Employment status and income
2. Debt obligations and ratios
3. Any notable strengths or concerns

Keep the tone professional and objective.
""")

borrower_profile_with_decision_types_prompt = ChatPromptTemplate.from_template("""
You are a senior loan underwriter analyzing a mortgage loan application.

Based on the financial data and pre-calculated ratios, return a structured JSON object including:
1. Borrower information
2. Financial ratios (do not recalculate)
3. Risk assessment (bullet format)
4. A classified decision type: "Approve", "Deny", or "Refer"
5. A loan decision summary in ≤ 20 words, written professionally from an underwriter's perspective

Use the following guidance for decision classification:
- **Approve**: Strong income, manageable debt, low LTV, adequate savings
- **Deny**: High DTI, very high LTV, poor credit, low income, or minimal reserves
- **Refer**: Mixed signals, borderline ratios, or missing information that requires human review

Borrower Data:
- Employment Title: {employment_title}
- Employer Name: {employer_name}
- Gross Annual Income: {gross_annual_income}
- Monthly Net Income: {monthly_net_income}
- Monthly Housing Expense: {monthly_housing_expense}
- Monthly Total Debt: {monthly_total_debt}
- Savings: {savings}
- Credit Used: {credit_used}
- Credit Limit: {credit_limit}
- Loan Amount: {loan_amount}
- Property Value: {property_value}

Financial Ratios:
Gross DTI (%): {gross_dti_percent}%
Back-End DTI (%): {back_dti_percent}%
LTV (%): {ltv_percent}%
Credit Utilization (%): {credit_utilization_percent}%
Savings-to-Income (%): {savings_to_income_percent}%
Net Worth-to-Income (%): {net_worth_to_income_percent}%

Output Format:
Return only a JSON object in this format:

{{
  "gross_annual_income": "{gross_annual_income}",
  "monthly_net_income": "{monthly_net_income}",
  "monthly_housing_expense": "{monthly_housing_expense}",
  "monthly_total_debt": "{monthly_total_debt}",
  "savings": "{savings}",
  "credit_used": "{credit_used}",
  "credit_limit": "{credit_limit}",
  "loan_amount": "{loan_amount}",
  "property_value": "{property_value}",

  "borrower_summary": "Job Title at Employer earning $X/year with $Y in monthly debt obligations.",

  "financial_ratios": {{
    "gross_dti_percent": "{gross_dti_percent}",
    "back_dti_percent": "{back_dti_percent}",
    "ltv_percent": "{ltv_percent}",
    "credit_utilization_percent": "{credit_utilization_percent}",
    "savings_to_income_percent": "{savings_to_income_percent}",
    "net_worth_to_income_percent": "{net_worth_to_income_percent}"
  }},

  "risk_assessment": [
    "Gross DTI (%): ⚠️ High Risk",
    "Back-End DTI (%): ✅ Low Risk",
    "LTV (%): ⚠️ High Risk",
    "Credit Utilization (%): ✅ Low Risk",
    "Savings-to-Income (%): ⚠️ Low",
    "Net Worth-to-Income (%): ⚠️ Weak"
  ],

  "decision_type": "Refer",

  "loan_decision_summary": "Refer for manual review due to elevated LTV and insufficient savings despite stable income."
}}

Rules:
- Do not modify input numbers
- Use only ✅ or ⚠️ in risk labels
- The `decision_type` must be exactly one of: "Approve", "Deny", or "Refer"
- Keep the `loan_decision_summary` concise, clear, and ≤ 20 words
- Do not include any content outside the JSON
""") 