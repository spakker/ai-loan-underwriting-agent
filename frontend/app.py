import gradio as gr
import requests
import json
import os

def analyze_documents(files):
    if not files:
        return "Please upload at least one document.", "No files uploaded.", ""
    
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
        
        # First, get text extraction results
        response = requests.post(
            "http://localhost:8000/analyze",
            files=files_data
        )
        
        if response.status_code == 200:
            text_result = response.json()
            
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
            response = requests.post(
                "http://localhost:8000/analyze/complete",
                files=files_data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Format the analysis output
                analysis_output = "### Financial Analysis Results\n\n"
                analysis_output += "#### Financial Ratios:\n"
                for metric, value in result["ratios"].items():
                    analysis_output += f"- {metric}: {value}%\n"
                
                analysis_output += "\n#### Risk Assessment:\n"
                for metric, assessment in result["risk_profile"].items():
                    analysis_output += f"- {metric}: {assessment}\n"
                    
                # Create a summary for the status
                status_output = "✅ Analysis Complete"
                    
                return analysis_output, text_output, status_output
            else:
                return f"Error in financial analysis: {response.text}", text_output, "❌ Analysis Failed"
        else:
            return f"Error: {response.text}", "Error processing files.", "❌ Analysis Failed"
            
    except Exception as e:
        return f"Error processing files: {str(e)}", "Error occurred during processing.", "❌ Analysis Failed"

# Create the Gradio interface
with gr.Blocks(title="Mortgage Risk Analysis") as demo:
    gr.Markdown(
        """
        # 🏠 Mortgage Risk Analysis
        Upload financial documents (PDF format) for comprehensive risk analysis.
        """
    )
    
    with gr.Row():
        # Left column for document upload and analysis
        with gr.Column(scale=1):
            with gr.Row():
                # Left side - Upload Documents
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 📄 Upload Documents")
                        file_input = gr.File(
                            file_count="multiple",
                            file_types=[".pdf"],
                            label="Upload Documents",
                            type="filepath"
                        )
                        analyze_btn = gr.Button("📊 Analyze Documents", variant="primary")
                        status_output = gr.Markdown()
                
                # Right side - Analysis Results
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 💹 Analysis Results")
                        analysis_output = gr.Markdown()
        
        # Right column for text extraction
        with gr.Column(scale=1):
            gr.Markdown("### 📝 Extracted Text")
            text_output = gr.Markdown()
    
    analyze_btn.click(
        fn=analyze_documents,
        inputs=[file_input],
        outputs=[analysis_output, text_output, status_output]
    )

if __name__ == "__main__":
    demo.launch()
