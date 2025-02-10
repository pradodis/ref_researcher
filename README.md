# Reference Researcher

A Python-based tool for academic reference management, citation analysis, and PDF document processing.

## Features

- Automated PDF document downloading from DOIs using available academic repositories
- Reference network analysis and visualization
- Document relevance scoring based on keywords
- PDF text extraction and analysisast data retrieval
- Redis-based caching system for fast data retrieval
- Citation network graph generationm CrossRef and OpenCitations
- Automated metadata extraction from CrossRef and OpenCitations

## Prerequisites

- Python 3.8 or higher
- Redis server (optional but recommended)
- Chrome browser (for PDF downloads)

## Installation

1. Clone the repository:

## Legal Disclaimer

This tool is for academic research purposes only. Users are responsible for ensuring their use complies with all applicable laws and terms of service. The automated downloading of PDFs requires appropriate access rights and subscriptions to the respective publishers. Please ensure you have the necessary permissions before downloading any content.

## API Usage
- CrossRef API: Please provide your email in config.ini as requested by CrossRef API best practices
- OpenCitations API: Usage subject to their terms of service
- Rate limiting is implemented to respect API services

## Data Protection
- No credentials are stored in the code
- Use config.ini for all sensitive settings
- Redis database should be properly secured if used

## Configuration

1. Copy `config.example.ini` to `config.ini`
2. Edit `config.ini` with your settings control
3. Never commit `config.ini` to version control