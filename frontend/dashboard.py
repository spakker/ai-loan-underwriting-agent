import gradio as gr
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from prompts import borrower_summary_prompt
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def format_currency(amount):
    return f"${amount:,.2f}"

def format_ratio_value(ratio_type, value):
    if ratio_type == "dscr":
        return f"{value:.2f}"
    return f"{value}%"

def generate_borrower_summary(data):
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
    )
    
    # Prepare the data for the prompt
    prompt_data = {
        "employment": data["borrower"]["employment"],
        "annual_income": format_currency(data["borrower"]["annual_income"]),
        "monthly_debt": format_currency(data["borrower"]["monthly_debt"]),
        "dti": data["ratios"]["dti"]["value"],
        "dscr": data["ratios"]["dscr"]["value"],
        "ltv": data["ratios"]["ltv"]["value"]
    }
    
    # Generate the summary
    chain = borrower_summary_prompt | llm
    summary = chain.invoke(prompt_data)
    return summary.content

def get_loan_application_data():
    # This would typically fetch data from your backend
    # Mocking the data for now
    return {
        "borrower": {
            "name": "[REDACTED]",
            "employment": "Self-employed",
            "annual_income": 85000,
            "monthly_debt": 1200
        },
        "ratios": {
            "dti": {
                "value": 36,
                "required": "≤ 43%",
                "status": "pass"
            },
            "dscr": {
                "value": 0.95,
                "required": "≥ 1.2",
                "status": "fail"
            },
            "ltv": {
                "value": 78,
                "required": "≤ 80%",
                "status": "pass"
            }
        },
        "risk_flags": [
            "DSCR below threshold (Required ≥ 1.2)",
            "Self-employed income without 2-year proof"
        ],
        "decision": {
            "status": "Conditional Approval",
            "message": "Application shows promise but requires additional documentation",
            "followup": "Please upload business bank statements from the last 6 months to verify self-employment income."
        }
    }

def update_financial_ratios(computed_ratios=None):
    data = get_loan_application_data()
    
    if computed_ratios:
        # Update the ratios with computed values while keeping the requirements
        for metric, value in computed_ratios.items():
            metric_key = metric.lower()
            if metric_key in data['ratios']:
                # Handle percentage values from API
                if isinstance(value, str) and '%' in value:
                    value = float(value.strip('%'))
                data['ratios'][metric_key]['value'] = float(value)
                # Update pass/fail status based on requirements
                if metric_key == 'dti':
                    data['ratios'][metric_key]['status'] = 'pass' if data['ratios'][metric_key]['value'] <= 43 else 'fail'
                elif metric_key == 'dscr':
                    data['ratios'][metric_key]['status'] = 'pass' if data['ratios'][metric_key]['value'] >= 1.2 else 'fail'
                elif metric_key == 'ltv':
                    data['ratios'][metric_key]['status'] = 'pass' if data['ratios'][metric_key]['value'] <= 80 else 'fail'
    
    # Financial Ratios Section
    ratios_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3 style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2em;">📊</span> Financial Ratios
        </h3>
        <div style="margin-top: 15px;">
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>DTI</span>
                    <span style="color: {'#22c55e' if data['ratios']['dti']['status'] == 'pass' else '#ef4444'}">
                        {format_ratio_value('dti', data['ratios']['dti']['value'])}
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['dti']['required']}</div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>DSCR</span>
                    <span style="color: {'#22c55e' if data['ratios']['dscr']['status'] == 'pass' else '#ef4444'}">
                        {format_ratio_value('dscr', data['ratios']['dscr']['value'])}
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['dscr']['required']}</div>
            </div>
            
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>LTV</span>
                    <span style="color: {'#22c55e' if data['ratios']['ltv']['status'] == 'pass' else '#ef4444'}">
                        {format_ratio_value('ltv', data['ratios']['ltv']['value'])}
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['ltv']['required']}</div>
            </div>
        </div>
    </div>
    """
    return ratios_html

def create_empty_dashboard():
    empty_html = """
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="color: #6b7280; text-align: center;">
            Awaiting document analysis...
        </div>
    </div>
    """
    return empty_html, empty_html, empty_html, empty_html

def update_dashboard(result, decision_result):
    print("\n=== Dashboard Update Started ===")
    print(f"Received result: {result}")
    print(f"Received decision_result: {decision_result}")
    
    if not result or not decision_result:
        print("Missing required data, creating empty dashboard")
        return create_empty_dashboard()
    
    try:
        # Extract employment info and ratios
        employment_title = result.get('employment_title', 'Not Available')
        employer_name = result.get('employer_name', 'Not Available')
        gross_annual_income = result.get('gross_annual_income', 0)
        monthly_net_income = result.get('monthly_net_income', 0)
        ratios = result.get('ratios', {})
        
        print("\nExtracted Data:")
        print(f"Employment: {employment_title} at {employer_name}")
        print(f"Income: ${gross_annual_income:,.2f} annual, ${monthly_net_income:,.2f} monthly")
        print(f"Ratios: {ratios}")

        # Loan Decision Section (for decision-section)
        print("\nGenerating Loan Decision")
        decision_type = decision_result.get('decision_type', 'Pending')
        print(f"Decision type: {decision_type}")
        decision_color = {
                'Approve': '#22c55e',           # Green - positive
                'Conditionally Approve': '#f59e0b',  # Amber - cautious optimism
                'Refer': '#eab308',             # Yellow - neutral review needed
                'Deny': '#ef4444'              # Red - negative
                }.get(decision_type, '#6b7280')     # Gray - fallback
        
        empathetic_message = decision_result.get('empathetic_message', 'Decision pending...')
        recommendations = decision_result.get('recommendations', [])
        
        recommendations_html = ""
        if recommendations:
            rec_list_items = "".join(f"<li>{item}</li>" for item in recommendations)
            recommendations_html = f"<ul>{rec_list_items}</ul>"

        decision_html = f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 25px; width: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="display: flex; align-items: center; gap: 10px; margin: 0;">
                    Loan Decision
                </h3>
                <div style="display: inline-block; background: {decision_color}; padding: 4px 12px; border-radius: 4px; color: white; font-size: 1.1em;">
                    {decision_type}
                </div>
            </div>
            <div style="background: #fffbeb; border-radius: 8px; padding: 20px; margin-top: 15px;">
                <div style="color: #92400e; font-size: 1.1em; margin-bottom: 10px;">{empathetic_message}</div>
                <div style="color: #92400e; font-size: 1.0em;">{recommendations_html}</div>
            </div>
        </div>
        """
        print("Loan Decision generated")
        
        # Borrower Summary Section (for borrower-section)
        print("\nGenerating Borrower Summary")
        borrower_html = f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                Borrower Summary
            </h3>
            <div style="margin-top: 15px;">
                <div style="margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span style="color: #666;">Annual Income</span>
                    <span>${gross_annual_income:,.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #666;">Monthly Net Income</span>
                    <span>${monthly_net_income:,.2f}</span>
                </div>
            </div>
        </div>
        """
        print("Borrower Summary generated")

        # Financial Ratios Section (for ratios-section)
        print("\nGenerating Financial Ratios")
        print(f"Working with ratios: {ratios}")
        
        # Helper function to get ratio value and determine color
        def get_ratio_display(ratio_name, value, threshold, higher_is_better=False):
            try:
                value = float(value)
                
                # Validate the value is reasonable
                if not (0 <= value <= 1000):  # Allow reasonable range for percentages
                    logger.warning(f"Ratio {ratio_name} has unreasonable value: {value}")
                    return 'N/A', '#6b7280'
                
                # Handle special cases
                if ratio_name == 'CreditUtilization' and value > 100:
                    # Credit utilization can exceed 100% if over limit
                    color = '#ef4444'  # Always red if over 100%
                elif higher_is_better:
                    color = '#22c55e' if value >= threshold else '#ef4444'
                else:
                    color = '#22c55e' if value <= threshold else '#ef4444'
                
                return value, color
            except (ValueError, TypeError):
                return 'N/A', '#6b7280'
        
        # Define ratio thresholds and display names
        ratio_configs = {
            'DTI': {'threshold': 43, 'display': 'DTI (Debt-to-Income)', 'higher_is_better': False, 'required': '≤ 43%'},
            'BackEndDTI': {'threshold': 36, 'display': 'Back-End DTI', 'higher_is_better': False, 'required': '≤ 36%'},
            'LTV': {'threshold': 80, 'display': 'LTV (Loan-to-Value)', 'higher_is_better': False, 'required': '≤ 80%'},
            'CreditUtilization': {'threshold': 30, 'display': 'Credit Utilization', 'higher_is_better': False, 'required': '≤ 30%'},
            'SavingsToIncome': {'threshold': 10, 'display': 'Savings to Income', 'higher_is_better': True, 'required': '≥ 10%'},
            'NetWorthToIncome': {'threshold': 0, 'display': 'Net Worth to Income', 'higher_is_better': True, 'required': '≥ 0%'}
        }
        
        # Generate ratio HTML elements
        ratio_elements = []
        for ratio_key, config in ratio_configs.items():
            if ratio_key in ratios:
                value, color = get_ratio_display(
                    ratio_key, 
                    ratios[ratio_key], 
                    config['threshold'],
                    config['higher_is_better']
                )
                ratio_elements.append(f"""
                    <div style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>{config['display']}</span>
                            <span style="color: {color}">
                                {value if value == 'N/A' else f'{value:.1f}%'}
                            </span>
                        </div>
                        <div style="color: #666; font-size: 0.9em;">Required: {config['required']}</div>
                    </div>
                """)
        
        ratios_html = f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                Financial Ratios
            </h3>
            <div style="margin-top: 15px;">
                {''.join(ratio_elements)}
            </div>
        </div>
        """
        print("Financial Ratios generated")

        # Risk Assessment Section (for risk-section)
        print("\nGenerating Risk Assessment")
        risk_flags = decision_result.get('risk_assessment', {})
        print(f"Working with risk flags: {risk_flags}")

        risk_items_html = []
        if isinstance(risk_flags, dict):
            for key, value in risk_flags.items():
                # Reformat the key to be more human-readable
                display_key = key.replace('_', ' ').replace(' percent', ' (%)').title()
                risk_items_html.append(f'<li>{display_key}: {value}</li>')
        elif isinstance(risk_flags, list): # Fallback for old list format
             for risk in risk_flags:
                risk_items_html.append(f'<li>{risk}</li>')

        risk_html = f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                Risk Assessment
            </h3>
            <div style="background: #fef2f2; border-radius: 8px; padding: 15px; margin-top: 15px;">
                <div style="color: #dc2626; margin-bottom: 10px;">Risk Flags Identified:</div>
                <ul style="color: #dc2626; margin: 0; padding-left: 20px;">
                    {''.join(risk_items_html) if risk_items_html else '<li>No risk flags identified</li>'}
                </ul>
            </div>
        </div>
        """
        print("Risk Assessment generated")

        print("\n=== Dashboard Update Completed ===")
        # Return order matches the element IDs in app.py:
        # risk-section (top), borrower-section, decision-section, ratios-section
        return decision_html,risk_html, borrower_html,ratios_html
        
    except Exception as e:
        print(f"Error in update_dashboard: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_empty_dashboard()

def create_dashboard_interface():
    dashboard = gr.Blocks(
        title="Agnetic Loan Application",
        css="""
            body {
                background-color: #f3f4f6 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            #dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .status-badge {
                position: absolute;
                top: 20px;
                right: 20px;
                background: #fef3c7;
                color: #92400e;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 500;
            }
            h1 {
                font-size: 2.25rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: #111827;
            }
            h2 {
                font-size: 1.5rem;
                font-weight: 500;
                color: #4b5563;
                margin-bottom: 2rem;
            }
            .gradio-row {
                gap: 1rem !important;
            }
            .gradio-html > div {
                height: 100%;
            }
            .gradio-dropdown {
                background: white !important;
            }
            .gradio-textbox {
                background: white !important;
            }
            .gradio-button.primary {
                background: #2563eb !important;
                color: white !important;
            }
            .gradio-button.primary:hover {
                background: #1d4ed8 !important;
            }
        """
    )
    
    with dashboard:
        with gr.Column(elem_id="dashboard-container"):
            gr.Markdown(
                """
                # Agnetic Loan Application
                ## Application Review Dashboard
                """
            )
            
            status_badge = gr.Markdown(
                """
                <div class="status-badge">Awaiting Documents</div>
                """,
                elem_classes=["status-container"]
            )
            
            with gr.Row(equal_height=True):
                borrower_html = gr.HTML(visible=True, elem_id="borrower-section")
                ratios_html = gr.HTML(visible=True, elem_id="ratios-section")
                risk_html = gr.HTML(visible=True, elem_id="risk-section")
            
            decision_html = gr.HTML(visible=True, elem_id="decision-section")
            
            # Initialize the dashboard with empty state
            empty_components = create_empty_dashboard()
            print("\n=== Initializing Dashboard ===")
            print(f"Number of empty components: {len(empty_components)}")
            
            dashboard.load(
                fn=lambda: empty_components,
                outputs=[borrower_html, ratios_html, risk_html, decision_html]
            )
    
    return dashboard

if __name__ == "__main__":
    demo = create_dashboard_interface()
    demo.launch() 