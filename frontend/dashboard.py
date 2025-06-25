import gradio as gr

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

def create_dashboard():
    data = get_loan_application_data()
    
    # Borrower Summary Section
    borrower_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3 style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2em;">👤</span> Borrower Summary
        </h3>
        <table style="width: 100%;">
            <tr>
                <td style="padding: 8px 0;">Name:</td>
                <td style="text-align: right;">{data['borrower']['name']}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Employment:</td>
                <td style="text-align: right;">
                    <span style="display: flex; align-items: center; justify-content: flex-end;">
                        <span style="margin-right: 5px;">📋</span>
                        {data['borrower']['employment']}
                    </span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Annual Income:</td>
                <td style="text-align: right;">{format_currency(data['borrower']['annual_income'])}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Monthly Debt:</td>
                <td style="text-align: right;">{format_currency(data['borrower']['monthly_debt'])}</td>
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
                    <span style="color: {'#22c55e' if data['ratios']['dti']['status'] == 'pass' else '#ef4444'}">
                        {data['ratios']['dti']['value']}%
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['dti']['required']}</div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>DSCR</span>
                    <span style="color: {'#22c55e' if data['ratios']['dscr']['status'] == 'pass' else '#ef4444'}">
                        {data['ratios']['dscr']['value']}
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['dscr']['required']}</div>
            </div>
            
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>LTV</span>
                    <span style="color: {'#22c55e' if data['ratios']['ltv']['status'] == 'pass' else '#ef4444'}">
                        {data['ratios']['ltv']['value']}%
                    </span>
                </div>
                <div style="color: #666; font-size: 0.9em;">Required: {data['ratios']['ltv']['required']}</div>
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
                {chr(10).join(f'<li>{flag}</li>' for flag in data['risk_flags'])}
            </ul>
        </div>
    </div>
    """

    # Loan Decision Section
    decision_html = f"""
    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
        <h3 style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <span style="font-size: 1.2em;">✅</span> Loan Decision
        </h3>
        <div style="background: #fffbeb; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: inline-block; background: #fef3c7; padding: 4px 8px; border-radius: 4px; font-size: 0.9em;">
                Conditional Approval
            </div>
            <div style="margin-top: 10px; color: #92400e;">{data['decision']['message']}</div>
        </div>
        <div style="background: #eff6ff; border-radius: 8px; padding: 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2em;">📋</span>
                <span style="font-weight: 500;">Suggested Follow-up:</span>
            </div>
            <div style="color: #1d4ed8; margin-top: 8px;">"{data['decision']['followup']}"</div>
        </div>
    </div>
    """

    return borrower_html, ratios_html, risk_html, decision_html

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
            
            gr.Markdown(
                """
                <div class="status-badge">Under Review</div>
                """,
                elem_classes=["status-container"]
            )
            
            with gr.Row(equal_height=True):
                borrower_html = gr.HTML()
                ratios_html = gr.HTML()
                risk_html = gr.HTML()
                
            decision_html = gr.HTML()
            
            # Add Request Section
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📝 New Request")
                    with gr.Row():
                        request_type = gr.Dropdown(
                            choices=["bank_statements", "employment", "income", "custom"],
                            value="bank_statements",
                            label="Request Type",
                            type="value"
                        )
                        custom_message = gr.Textbox(
                            label="Custom Message",
                            placeholder="Enter your custom request message here...",
                            visible=False
                        )
                    
                    submit_btn = gr.Button("📤 Submit Request", variant="primary")
                    request_status = gr.Markdown()
                    
                    def update_custom_message_visibility(request_type):
                        return {"visible": request_type == "custom"}
                    
                    request_type.change(
                        fn=update_custom_message_visibility,
                        inputs=[request_type],
                        outputs=[custom_message]
                    )
                    
                    submit_btn.click(
                        fn=submit_request,
                        inputs=[request_type, custom_message],
                        outputs=[request_status]
                    )
            
            # Update the dashboard on page load
            dashboard.load(
                fn=create_dashboard,
                outputs=[borrower_html, ratios_html, risk_html, decision_html]
            )
    
    return dashboard

if __name__ == "__main__":
    demo = create_dashboard_interface()
    demo.launch() 