from setuptools import setup, find_packages

setup(
    name="ai-loan-underwriting-agent",
    version="0.1.0",
    packages=find_packages(include=[
        "backend",
        "backend.*",
        "frontend",
        "frontend.*",
        "rag",
        "rag.*",
        "shared",
        "shared.*"
    ]),
    install_requires=[
        "fastapi",
        "python-multipart",
        "PyPDF2",
        "python-dotenv",
        "langchain-openai",
        "pydantic",
        "langchain"
    ],
    python_requires=">=3.8",
) 