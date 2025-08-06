from pathlib import Path

from setuptools import find_packages, setup

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"

# Fallback to empty list if requirements.txt is missing (e.g., during certain
# CI stages where dependencies are injected differently).
if REQUIREMENTS_FILE.exists():
    with REQUIREMENTS_FILE.open("r", encoding="utf-8") as fp:
        install_requires = [line.strip() for line in fp if line.strip() and not line.startswith("#")]
else:
    install_requires = []

# ----------------------------------------------------------------------------
# Package configuration
# ----------------------------------------------------------------------------

setup(
    name="financial_analyzer",
    version="0.1.0",
    description="Pipeline for scraping financial news, generating embeddings and storing them in a vector DB",
    author="Your Name",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=install_requires,
    python_requires=">=3.9",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

