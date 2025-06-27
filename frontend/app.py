import gradio as gr
import requests
import json
import os
from dashboard import create_dashboard_interface, update_dashboard, create_empty_dashboard
from evaluation_interface import create_evaluation_interface
from langchain_openai import ChatOpenAI
from prompts import borrower_profile_with_decision_types_prompt

def format_currency(amount):
    return f"${amount:,.2f}"

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

def get_loan_decision(result):
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,
    )
    
    # Prepare the data for the prompt
    prompt_data = {
        "employment_title": result.get("employment_title", "Not Available"),
        "employer_name": result.get("employer_name", "Not Available"),
        "gross_annual_income": format_currency(result.get("gross_annual_income", 0)),
        "monthly_net_income": format_currency(result.get("monthly_net_income", 0)),
        "monthly_housing_expense": format_currency(result.get("monthly_housing_expense", 0)),
        "monthly_total_debt": format_currency(result.get("monthly_total_debt", 0)),
        "savings": format_currency(result.get("savings", 0)),
        "credit_used": format_currency(result.get("credit_used", 0)),
        "credit_limit": format_currency(result.get("credit_limit", 0)),
        "loan_amount": format_currency(result.get("loan_amount", 0)),
        "property_value": format_currency(result.get("property_value", 0)),
        "gross_dti_percent": result.get("ratios", {}).get("DTI", "0"),
        "back_dti_percent": result.get("ratios", {}).get("BackEndDTI", "0"),
        "ltv_percent": result.get("ratios", {}).get("LTV", "0"),
        "credit_utilization_percent": result.get("ratios", {}).get("CreditUtilization", "0"),
        "savings_to_income_percent": result.get("ratios", {}).get("SavingsToIncome", "0"),
        "net_worth_to_income_percent": result.get("ratios", {}).get("NetWorthToIncome", "0")
    }
    
    # Generate the decision
    chain = borrower_profile_with_decision_types_prompt | llm
    response = chain.invoke(prompt_data)
    
    try:
        # Try to get the content attribute first
        response_text = response.content if hasattr(response, 'content') else str(response)
        if isinstance(response_text, (list, dict)):
            response_text = str(response_text)
        
        # Parse the JSON response
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Return a default structure if JSON parsing fails
        return {
            "risk_assessment": [
                "Error: Unable to process risk assessment"
            ],
            "decision_type": "Refer",
            "loan_decision_summary": "System error - manual review required"
        }

def submit_request(request_type, custom_message):
    # This would typically send the request to your backend
    # For now, we'll just return a success message
    if request_type == "custom" and not custom_message:
        return "❌ Please provide a custom message for your request."
    
    request_types = {
        "bank_statements": "Requested additional bank statements",
        "employment": "Requested employment verification",
        "income": "Requested income verification",
        "custom": f"Custom request: {custom_message}"
    }
    
    return f"✅ {request_types[request_type]} - Request sent successfully!"

def create_dashboard(result, decision_result):
    # Borrower Summary Section
    borrower_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3 style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2em;">👤</span> Borrower Summary
        </h3>
        <table style="width: 100%;">
            <tr>
                <td style="padding: 8px 0;">Employment Title:</td>
                <td style="text-align: right;">{result.get("employment_title", "Not Available")}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Employer:</td>
                <td style="text-align: right;">
                    <span style="display: flex; align-items: center; justify-content: flex-end;">
                        <span style="margin-right: 5px;">📋</span>
                        {result.get("employer_name", "Not Available")}
                    </span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Annual Income:</td>
                <td style="text-align: right;">{format_currency(result.get("gross_annual_income", 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Monthly Net Income:</td>
                <td style="text-align: right;">{format_currency(result.get("monthly_net_income", 0))}</td>
            </tr>
        </table>
    </div>
    """

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
                    <span style="color: {'#22c55e' if float(result.get('ratios', {}).get('DTI', '100')) <= 43 else '#ef4444'}">
                        {result.get('ratios', {}).get('DTI', 'N/A')}%
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: ≤ 43%</div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>Back-End DTI</span>
                    <span style="color: {'#22c55e' if float(result.get('ratios', {}).get('BackEndDTI', '100')) <= 36 else '#ef4444'}">
                        {result.get('ratios', {}).get('BackEndDTI', 'N/A')}%
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: ≤ 36%</div>
            </div>
            
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>LTV</span>
                    <span style="color: {'#22c55e' if float(result.get('ratios', {}).get('LTV', '100')) <= 80 else '#ef4444'}">
                        {result.get('ratios', {}).get('LTV', 'N/A')}%
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: ≤ 80%</div>
            </div>
        </div>
    </div>
    """

    # Risk Assessment Section
    risk_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3 style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2em;">⚠️</span> Risk Assessment
        </h3>
        <div style="background: #fef2f2; border-radius: 8px; padding: 15px; margin-top: 15px;">
            <div style="color: #dc2626; margin-bottom: 10px;">Risk Flags Identified:</div>
            <ul style="color: #dc2626; margin: 0; padding-left: 20px;">
                {chr(10).join(f'<li>{risk}</li>' for risk in decision_result.get('risk_assessment', []))}
            </ul>
        </div>
    </div>
    """

    # Loan Decision Section
    decision_type = decision_result.get('decision_type', 'Pending')
    decision_color = {
        'Approve': '#22c55e',
        'Deny': '#ef4444',
        'Refer': '#eab308'
    }.get(decision_type, '#6b7280')
    
    decision_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
        <h3 style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <span style="font-size: 1.2em;">✅</span> Loan Decision
        </h3>
        <div style="background: #fffbeb; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: inline-block; background: {decision_color}; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; color: white;">
                {decision_type}
            </div>
            <div style="margin-top: 10px; color: #92400e;">{decision_result.get('loan_decision_summary', 'Decision pending...')}</div>
        </div>
    </div>
    """

    return borrower_html, ratios_html, risk_html, decision_html

def analyze_documents(files):
    if not files:
        return "Please upload at least one document.", "No files uploaded.", "", None, None
    
    try:
        # Create a list of file tuples for the request
        files_data = []
        for file in files:
            # Handle file path from Gradio
            if isinstance(file, str):
                with open(file, 'rb') as f:
                    filename = os.path.basename(file)
                    content = f.read()
                    files_data.append(('files', (filename, content, 'application/pdf')))
            else:
                # Fallback for other file types
                files_data.append(('files', (file.name, file, 'application/pdf')))
        
        print("\n=== Making API Requests ===")
        # First, get text extraction results
        response = requests.post(
            "http://localhost:8000/analyze",
            files=files_data
        )
        
        if response.status_code == 200:
            text_result = response.json()
            print("Text extraction response:", text_result)
            
            # Format the text extraction output
            text_output = "### Text Extraction Results:\n"
            text_output += f"Total Characters: {text_result['text_summary']['total_characters']}\n\n"
            
            for file_info in text_result['text_summary']['files']:
                text_output += f"**File: {file_info['file_name']}**\n"
                text_output += f"Characters: {file_info['characters']}\n"
                text_output += "Preview:\n```\n"
                text_output += file_info['preview']
                text_output += "\n```\n\n"
            
            # Now proceed with complete analysis
            print("\n=== Making Complete Analysis Request ===")
            response = requests.post(
                "http://localhost:8000/analyze/complete",
                files=files_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\nComplete analysis response:", result)
                
                # Extract employment info from risk profile
                print("\nResult:", result)
    
                employment_info = result.get('risk_profile', {})
                result.update({
                    'employment_title': employment_info.get('employment_title', 'Not Available'),
                    'employer_name': employment_info.get('employer_name', 'Not Available'),
                    'gross_annual_income': float(employment_info.get('gross_annual_income', 0)),
                    'monthly_net_income': float(employment_info.get('monthly_net_income', 0))
                })
                
                # Ensure ratios are in the correct format
                if 'ratios' not in result:
                    result['ratios'] = {}
                
                # Get loan decision using LLM
                decision_result = get_loan_decision(result)
                print("\nDecision Result:", decision_result)
                
                # Format the analysis output
                analysis_output = "### Financial Analysis Results\n\n"
                analysis_output += "#### Financial Ratios:\n"
                for metric, value in result.get("ratios", {}).items():
                    if isinstance(value, (int, float)):
                        analysis_output += f"- {metric}: {value:.1f}%\n"
                    else:
                        analysis_output += f"- {metric}: {value}\n"
                
                analysis_output += "\n#### Risk Assessment:\n"
                for risk_item in decision_result.get("risk_assessment", []):
                    analysis_output += f"- {risk_item}\n"
                
                analysis_output += f"\n#### Decision Type: {decision_result.get('decision_type', 'Pending')}\n"
                analysis_output += f"Summary: {decision_result.get('loan_decision_summary', 'Decision pending...')}\n"
                    
                # Create a summary for the status
                status_output = "✅ Analysis Complete"
                    
                # Print debug information
                print("\n=== Final Data for Dashboard ===")
                print("Result data:", result)
                print("Decision result data:", decision_result)
                
                return analysis_output, text_output, status_output, result, decision_result
            else:
                error_msg = f"Error in financial analysis: {response.text}"
                print("\nAPI Error:", error_msg)
                return error_msg, text_output, "❌ Analysis Failed", None, None
        else:
            error_msg = f"Error: {response.text}"
            print("\nAPI Error:", error_msg)
            return error_msg, "Error processing files.", "❌ Analysis Failed", None, None
            
    except Exception as e:
        error_msg = f"Error processing files: {str(e)}"
        print("\nException:", error_msg)
        return error_msg, "Error occurred during processing.", "❌ Analysis Failed", None, None

def process_analysis(files):
    print("\n=== Starting Document Analysis ===")
    print(f"Input files: {files}")
    
    output = analyze_documents(files)
    print("\n=== Raw Analysis Output ===")
    print(f"Output length: {len(output)}")
    print(f"Output contents: {output}")
    
    # Unpack all values, using None as default for missing values
    analysis_output = output[0] if len(output) > 0 else None
    text_output = output[1] if len(output) > 1 else None
    status_output = output[2] if len(output) > 2 else None
    result = output[3] if len(output) > 3 else {}
    decision_result = output[4] if len(output) > 4 else {}
    
    print("\n=== Unpacked Analysis Results ===")
    print(f"Analysis Output: {analysis_output}")
    print(f"Text Output: {text_output}")
    print(f"Status Output: {status_output}")
    print(f"Result: {result}")
    print(f"Decision Result: {decision_result}")
    
    if result and decision_result:
        print("\n=== Updating Dashboard ===")
        from dashboard import update_dashboard
        try:
            dashboard_html = update_dashboard(result, decision_result)
            print(f"Dashboard HTML components generated: {len(dashboard_html)} components")
            print("First 100 chars of each component:")
            for i, html in enumerate(dashboard_html):
                print(f"Component {i}: {str(html)[:100]}...")
            return [
                analysis_output or "",
                text_output or "",
                status_output or "",
                *dashboard_html  # Unpack the dashboard HTML components
            ]
        except Exception as e:
            print(f"Error updating dashboard: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            from dashboard import create_empty_dashboard
            return [
                analysis_output or "",
                text_output or "",
                status_output or "",
                *create_empty_dashboard()
            ]
    else:
        print("\n=== Creating Empty Dashboard ===")
        print("No result or decision_result available")
        from dashboard import create_empty_dashboard
        empty_dashboard = create_empty_dashboard()
        print(f"Empty dashboard components: {len(empty_dashboard)}")
        return [
            analysis_output or "",
            text_output or "",
            status_output or "",
            *empty_dashboard
        ]

def create_upload_interface():
    upload = gr.Blocks(title="Document Upload")
    
    with upload:
        gr.Markdown(
            """
            Upload loan application (PDF format) for underwriter review and comprehensive risk analysis.
            """,
            elem_classes=["header-text"]
        )
        
        with gr.Row():
            # Left column for document upload
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📄 Upload Loan Application")
                    file_input = gr.File(
                        file_count="multiple",
                        file_types=[".pdf"],
                        label="Upload Loan Application",
                        type="filepath"
                    )
                    analyze_btn = gr.Button("📊 Analyze Loan Application", variant="primary")
                    status_output = gr.Markdown()
            
            # Right column for text extraction
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Extracted Text")
                text_output = gr.Markdown()
        
        # Components to update the dashboard
        borrower_output = gr.HTML(visible=False)
        ratios_output = gr.HTML(visible=False)
        risk_output = gr.HTML(visible=False)
        decision_output = gr.HTML(visible=False)
        
        analyze_btn.click(
            fn=process_analysis,
            inputs=[file_input],
            outputs=[
                text_output,
                status_output,
                borrower_output,
                ratios_output,
                risk_output,
                decision_output
            ]
        )
    
    return upload

# Create the main application with routes
def create_app():
    with gr.Blocks(title="Agnetic Loan Application") as app:
        # Shared state between tabs
        dashboard_state = gr.State({})
        decision_state = gr.State({})
        
        with gr.Tabs() as tabs:
            with gr.Tab("Upload"):
                # Create upload interface components
                gr.Markdown(
                    """
                    Upload loan application documents (PDF format) for underwriter review and comprehensive risk analysis.
                    """,
                    elem_classes=["header-text"]
                )
                
                with gr.Row():
                    # Left column for document upload
                    with gr.Column(scale=1):
                        gr.HTML("""
                            <div class="custom-box">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                                    <span style="font-size: 1.2em;">📄</span>
                                    <h3 style="margin: 0; color: #2B3674;">Loan Application</h3>
                                </div>
                            </div>
                        """)
                        with gr.Group(elem_classes=["custom-box-content"]):
                            file_input = gr.File(
                                file_count="multiple",
                                file_types=[".pdf"],
                                label="Loan Application Documents",
                                type="filepath"
                            )
                            analyze_btn = gr.Button("📊 Analyze Application", variant="primary")
                            status_output = gr.Markdown()
                    
                    # Right column for text extraction
                    with gr.Column(scale=1):
                        gr.HTML("""
                            <div class="custom-box">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                                    <span style="font-size: 1.2em;">📝</span>
                                    <h3 style="margin: 0; color: #2B3674;">Extracted Text</h3>
                                </div>
                            </div>
                        """)
                        with gr.Group(elem_classes=["custom-box-content"]):
                            text_output = gr.Markdown()
                
                # Add custom CSS
                gr.HTML("""
                    <style>
                    .header-text {
                        margin: 20px 0;
                        color: #2B3674;
                        font-size: 1.1em;
                    }
                    .custom-box {
                        background: white;
                        padding: 20px;
                        border-radius: 10px 10px 0 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .custom-box-content {
                        background: white;
                        padding: 20px;
                        border-radius: 0 0 10px 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        margin-top: -10px;
                    }
                    </style>
                """)
                
                # Components to update the dashboard
                borrower_output = gr.HTML(visible=False)
                ratios_output = gr.HTML(visible=False)
                risk_output = gr.HTML(visible=False)
                decision_output = gr.HTML(visible=False)
                
                # Define the analysis function with state
                def process_analysis_with_state(files, dashboard_state, decision_state):
                    output = analyze_documents(files)
                    
                    # Unpack values
                    text_output = output[1] if len(output) > 1 else None
                    status_output = output[2] if len(output) > 2 else None
                    result = output[3] if len(output) > 3 else {}
                    decision_result = output[4] if len(output) > 4 else {}
                    
                    # Update shared state
                    dashboard_state = result
                    decision_state = decision_result
                    
                    # Update dashboard components
                    if result and decision_result:
                        from dashboard import update_dashboard
                        dashboard_html = update_dashboard(result, decision_result)
                    else:
                        from dashboard import create_empty_dashboard
                        dashboard_html = create_empty_dashboard()
                    
                    return [
                        text_output or "",
                        status_output or "",
                        borrower_output,
                        decision_output,
                        ratios_output,
                        risk_output,
                        dashboard_state,
                        decision_state
                    ]
                
                # Set up the click event
                analyze_btn.click(
                    fn=process_analysis_with_state,
                    inputs=[
                        file_input,
                        dashboard_state,
                        decision_state
                    ],
                    outputs=[
                        text_output,
                        status_output,
                        borrower_output,
                        ratios_output,
                        risk_output,
                        decision_output,
                        dashboard_state,
                        decision_state
                    ]
                )
            
            with gr.Tab("Dashboard"):
                # Create dashboard interface components
                with gr.Column(elem_id="dashboard-container"):
                    gr.Markdown(
                        """
                      
                        ## Underwriter Risk Dashboard
                        """
                    )
                    
                    status_badge = gr.Markdown(
                        """
                        <div class="status-badge">Awaiting Loan Application</div>
                        """,
                        elem_classes=["status-container"]
                    )
                    
                    # Risk Assessment in its own row
                    with gr.Row():
                        with gr.Column(scale=1):
                            dashboard_decision = gr.HTML(visible=True, elem_id="decision-section")
                    
                    # Main sections row
                    with gr.Row(equal_height=True):
                        dashboard_risk = gr.HTML(visible=True, elem_id="risk-section")
                        dashboard_borrower = gr.HTML(visible=True, elem_id="borrower-section")
                        dashboard_ratios = gr.HTML(visible=True, elem_id="ratios-section")
                    
                    # Initialize with empty state
                    from dashboard import create_empty_dashboard
                    empty_components = create_empty_dashboard()
                    
                    # Update dashboard when state changes
                    def update_dashboard_from_state(dashboard_state, decision_state):
                        if dashboard_state and decision_state:
                            from dashboard import update_dashboard
                            return update_dashboard(dashboard_state, decision_state)
                        else:
                            from dashboard import create_empty_dashboard
                            return create_empty_dashboard()
                    
                    # Listen for state changes
                    dashboard_state.change(
                        fn=update_dashboard_from_state,
                        inputs=[dashboard_state, decision_state],
                        outputs=[
                            dashboard_decision,
                            dashboard_risk,
                            dashboard_borrower,
                            dashboard_ratios
                        ]
                    )
                    
                    decision_state.change(
                        fn=update_dashboard_from_state,
                        inputs=[dashboard_state, decision_state],
                        outputs=[
                            dashboard_decision,
                            dashboard_risk,
                            dashboard_borrower,
                            dashboard_ratios
                        ]
                    )
            
            # Evaluation Tab
            with gr.Tab("Model Evaluation"):
                evaluation_interface = create_evaluation_interface()
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.launch()
