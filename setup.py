from setuptools import setup, find_packages

setup(
    name="web_scraper_operations",
    version="0.1.0",
    description="Bietet classes und Flows um websites zu automatisieren",
    author="Paul Breier",
    packages=find_packages(),  # sucht automatisch alle Subpakete
    install_requires=[
        "selenium>=4.34.2",     # Abhängigkeiten hier angeben
        "requests>=2.32.2",
        "pyyaml>=6.0.2"
    ],
    python_requires=">=3.12",    # Mindestversion von Python
)