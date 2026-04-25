from setuptools import setup, find_packages

setup(
    name="incident-reporter",
    version="1.0.0",
    description="Python SDK for AI Incident Response System — 2-line integration for FastAPI, Flask, and Django",
    long_description=open("README.md", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="AI Incident Response",
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "fastapi": ["fastapi>=0.100.0", "starlette>=0.27.0"],
        "flask": ["flask>=2.0.0"],
        "django": ["django>=3.2"],
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-mock>=3.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Monitoring",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
