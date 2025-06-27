import gradio as gr
import requests
import json
from typing import Dict, Optional

def format_evaluation_results(eval_results: Optional[Dict] = None) -> str:
    """Format evaluation results into HTML with consistent styling.
    
    Args:
        eval_results: Dictionary containing evaluation metrics and metadata
        
    Returns:
        Formatted HTML string for display
    """
    if not eval_results:
        return """
        <div class="custom-box">
            <div style="color: #6b7280; text-align: center; padding: 20px;">
                No evaluation results available. Click "Run Evaluation" to begin.
            </div>
        </div>
        """
    
    # Format the metrics results
    metrics_html = ""
    for metric_name, metric_value in eval_results.get("metrics", {}).items():
        score = metric_value.get("score", 0)
        color = "#22c55e" if score >= 0.8 else "#eab308" if score >= 0.6 else "#ef4444"
        
        metrics_html += f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #2B3674;">{metric_name}</span>
                <span style="color: {color}; font-weight: 500;">
                    {score:.2%}
                </span>
            </div>
            <div style="height: 6px; background: #e5e7eb; border-radius: 3px; margin-top: 8px;">
                <div style="width: {score*100}%; height: 100%; background: {color}; border-radius: 3px;"></div>
            </div>
        </div>
        """
    
    # Format the overall results
    return f"""
    <div class="custom-box">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <span style="font-size: 1.2em;">📊</span>
            <h3 style="margin: 0; color: #2B3674;">Evaluation Results</h3>
        </div>
        <div style="margin-top: 15px;">
            {metrics_html}
        </div>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            <h4 style="margin-bottom: 10px; color: #2B3674;">Experiment Details</h4>
            <div style="color: #6b7280;">
                <div>Experiment: {eval_results.get("experiment_name", "N/A")}</div>
                <div>Total Samples: {eval_results.get("total_samples", 0)}</div>
                <div>Timestamp: {eval_results.get("timestamp", "N/A")}</div>
            </div>
        </div>
    </div>
    """

def run_evaluation() -> str:
    """Run model evaluation by calling the backend API.
    
    Returns:
        Formatted HTML string with evaluation results
    """
    try:
        response = requests.post("http://localhost:8000/evaluate")
        if response.status_code == 200:
            eval_results = response.json()
            return format_evaluation_results(eval_results)
        else:
            error_message = f"Error: {response.status_code} - {response.text}"
            print(error_message)
            return format_evaluation_results(None)
    except Exception as e:
        error_message = f"Error running evaluation: {str(e)}"
        print(error_message)
        return format_evaluation_results(None)

def create_evaluation_interface() -> gr.Column:
    """Create the evaluation interface with proper styling and components.
    
    Returns:
        Gradio Column containing the evaluation interface
    """
    with gr.Column() as evaluation_interface:
        # Header
        gr.Markdown(
            """
            ## Model Evaluation
            This section allows you to evaluate the loan underwriting model's performance 
            against a test dataset. The evaluation measures:
            
            - **Hallucination**: Detecting if the model makes unfounded claims
            - **Answer Relevance**: Ensuring responses are relevant to loan underwriting
            - **Context Precision**: Verifying proper use of provided information
            """,
            elem_classes=["header-text"]
        )
        
        # Results display
        results_html = gr.HTML(
            format_evaluation_results(None),
            elem_id="evaluation-results"
        )
        
        # Run button
        run_button = gr.Button(
            "🔄 Run Evaluation",
            variant="primary",
            size="lg"
        )
        
        # Connect the button to the evaluation function
        run_button.click(
            fn=run_evaluation,
            outputs=[results_html]
        )
        
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
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            </style>
        """)
    
    return evaluation_interface 