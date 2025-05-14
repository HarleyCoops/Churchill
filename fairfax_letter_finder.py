#!/usr/bin/env python3
# Fairfax Letter Finder Agent
# Purpose: Search for the original letter from Colonel Bryan Charles Fairfax to Winston Churchill
# that prompted Churchill's reply dated December 6, 1946

import argparse
import requests
import json
import sys
import os
import time
import io
import re
import concurrent.futures
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional, Tuple

# Try to import optional dependencies, with fallbacks for graceful degradation
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logging.warning("PIL not found. Image processing capabilities will be limited.")

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logging.warning("pytesseract not found. OCR capabilities will be disabled.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fairfax_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fairfax_finder")

# Archive API Information
# Note: These archive systems generally require approved researcher access
# and don't provide open public APIs. Below are the actual endpoints and access methods.

# Churchill Archives Centre
# Requires formal research request and approval: https://archives.chu.cam.ac.uk/researchers
CHURCHILL_ARCHIVES_BASE_URL = "https://archives.chu.cam.ac.uk/"
# Their actual catalogue is JANUS: https://janus.lib.cam.ac.uk/db/node.xsp?id=EAD%2FGBR%2F0014
# Direct access to Churchill Papers requires subscription: https://www.churchillarchive.com/

# Library and Archives Canada 
# Uses Aurora system for search: https://recherche-collection-search.bac-lac.gc.ca/eng/home/record
LAC_ARCHIVES_BASE_URL = "https://recherche-collection-search.bac-lac.gc.ca/eng/home/"

# University of Toronto Archives
# Uses AtoM (Access to Memory) platform: https://utarms.library.utoronto.ca/
TORONTO_ARCHIVES_BASE_URL = "https://utarms.library.utoronto.ca/"

# API Endpoints mapping
# These are mapped based on known catalog structures, but most archives
# don't provide direct API access without approved research account
ARCHIVE_ENDPOINTS = {
    "churchill": {
        "search": "search",  # Actual endpoint requires authentication
        "item": "archives/record",
        "collection": "archives/collection",
    },
    "lac": {
        "search": "record",  # Main search interface
        "item": "item",
    },
    "toronto": {
        "search": "index.php/informationobject/browse",  # AtoM search interface
    }
}

# OCR Configuration
OCR_OUTPUT_DIR = "ocr_results"
DOWNLOAD_DIR = "downloaded_documents"
MAX_DOWNLOAD_RETRIES = 3
RATE_LIMIT_DELAY = 1.0  # Seconds between API calls to avoid rate limiting

# Archive Information
ARCHIVES = [
    {
        "name": "Churchill Archives Centre",
        "base_url": CHURCHILL_ARCHIVES_BASE_URL,
        "endpoints": ARCHIVE_ENDPOINTS["churchill"],
        "api_key_env": "CHURCHILL_API_KEY",
        "collections": ["CHAR", "CHUR"]
    },
    {
        "name": "Library and Archives Canada",
        "base_url": LAC_ARCHIVES_BASE_URL,
        "endpoints": ARCHIVE_ENDPOINTS["lac"],
        "api_key_env": "LAC_API_KEY",
        "collections": ["MG30", "RG24"]
    },
    {
        "name": "University of Toronto Archives",
        "base_url": TORONTO_ARCHIVES_BASE_URL,
        "endpoints": ARCHIVE_ENDPOINTS["toronto"],
        "api_key_env": "UTARMS_API_KEY",
        "collections": ["B1994-0002", "B2015-0005"]
    }
]

class ArchiveAPIClient:
    """Client for interacting with archive APIs.
    
    Note: Most archives require formal research requests and don't provide public APIs.
    To use this with real archives, you would need to:
    1. Submit research requests to the archives (often requires institutional affiliation)
    2. Obtain necessary credentials and access permissions
    3. Follow each archive's specific access protocols
    
    Current archives and access methods:
    - Churchill Archives: Requires application for reader's ticket and on-site access
      or subscription to Churchill Archive (https://www.churchillarchive.com/)
    - Library and Archives Canada: Requires formal application for access to restricted materials
    - University of Toronto Archives: Requires research appointment
    """
    
    def __init__(self, archive_config: Dict[str, Any]):
        self.name = archive_config["name"]
        self.base_url = archive_config["base_url"]
        self.endpoints = archive_config["endpoints"]
        self.collections = archive_config["collections"]
        
        # Get API key from environment variable if available
        # Note: Real archive access often requires more than just an API key
        # (cookies, session tokens, IP authentication, etc.)
        self.api_key = os.environ.get(archive_config["api_key_env"], None)
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
            
        # For Churchill Archives specifically, many resources require subscription
        if self.name == "Churchill Archives Centre" and self.api_key:
            # The actual Churchill Archive commercial product uses different authentication
            logger.info("Note: Churchill Archive typically requires subscription-based access")
        
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting to avoid overwhelming the API."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Perform a search using the archive's API."""
        self._rate_limit()
        
        endpoint = urljoin(self.base_url, self.endpoints["search"])
        logger.info(f"Searching {self.name} with query: {query}")
        
        try:
            # Construct the appropriate parameters for this specific archive
            search_params = self._prepare_search_params(query, params)
            
            response = self.session.get(endpoint, params=search_params)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error searching {self.name}: {str(e)}")
            return {"error": str(e), "results": []}
    
    def _prepare_search_params(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare search parameters for the specific archive API."""
        # This would be customized for each archive's API
        search_params = {
            "q": query,
            "page": params.get("page", 1),
            "limit": params.get("limit", 20)
        }
        
        # Add date range if provided
        if "start_date" in params and "end_date" in params:
            # Format depends on the specific API
            search_params["date_from"] = params["start_date"].strftime("%Y-%m-%d")
            search_params["date_to"] = params["end_date"].strftime("%Y-%m-%d")
        
        # Add collection filter if applicable
        if "collection" in params:
            search_params["collection"] = params["collection"]
        
        return search_params
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve document metadata using the archive's API."""
        self._rate_limit()
        
        endpoint = urljoin(self.base_url, urljoin(self.endpoints["item"], doc_id))
        logger.info(f"Retrieving document {doc_id} from {self.name}")
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error retrieving document {doc_id} from {self.name}: {str(e)}")
            return {"error": str(e)}
    
    def download_document_image(self, image_url: str, output_path: str) -> bool:
        """Download a document image from the archive."""
        self._rate_limit()
        
        logger.info(f"Downloading image from {self.name}: {image_url}")
        retries = 0
        
        while retries < MAX_DOWNLOAD_RETRIES:
            try:
                response = self.session.get(image_url, stream=True)
                response.raise_for_status()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Write the file
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Successfully downloaded to {output_path}")
                return True
            
            except requests.RequestException as e:
                retries += 1
                wait_time = retries * 2  # Exponential backoff
                logger.warning(f"Download attempt {retries} failed: {str(e)}. Retrying in {wait_time}s")
                time.sleep(wait_time)
        
        logger.error(f"Failed to download {image_url} after {MAX_DOWNLOAD_RETRIES} attempts")
        return False


class OCRProcessor:
    """Process scanned documents using OCR to extract text."""
    
    def __init__(self, output_dir: str = OCR_OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Check if OCR dependencies are available
        self.ocr_available = HAS_PIL and HAS_TESSERACT
        if not self.ocr_available:
            logger.warning("OCR functionality is disabled due to missing dependencies.")
            logger.warning("Please install required packages: pip install -r requirements.txt")
            logger.warning("And ensure Tesseract OCR is installed on your system.")
        
        # Set up pytesseract configuration if available
        if self.ocr_available:
            # You may need to specify the path to tesseract executable on some systems
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
                logger.info(f"Tesseract OCR version: {pytesseract.get_tesseract_version()}")
            except Exception as e:
                logger.error(f"Tesseract OCR is not correctly installed: {str(e)}")
                logger.error("Please install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
                self.ocr_available = False
    
    def process_image(self, image_path: str) -> str:
        """Process an image file using OCR and return extracted text."""
        if not self.ocr_available:
            logger.warning(f"Cannot process {image_path}: OCR functionality is disabled")
            return "[OCR UNAVAILABLE - INSTALL REQUIRED DEPENDENCIES]"
            
        try:
            logger.info(f"Processing image with OCR: {image_path}")
            image = Image.open(image_path)
            
            # Preprocess the image for better OCR results
            # This could include resizing, converting to grayscale, etc.
            # image = self._preprocess_image(image)
            
            # Perform OCR
            text = pytesseract.image_to_string(image, lang='eng')
            
            # Save the extracted text
            base_name = os.path.basename(image_path)
            text_file = os.path.join(self.output_dir, f"{os.path.splitext(base_name)[0]}.txt")
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"OCR completed. Text saved to {text_file}")
            return text
            
        except Exception as e:
            logger.error(f"OCR processing error for {image_path}: {str(e)}")
            return ""
    
    def process_document(self, doc_path: str) -> List[str]:
        """Process a multi-page document and return all extracted text."""
        # For PDF documents, we'd split into pages first
        # For now, just handle single images
        if doc_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')):
            return [self.process_image(doc_path)]
        else:
            logger.warning(f"Unsupported document format: {doc_path}")
            return []
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze extracted text for relevant information."""
        analysis = {
            "likely_correspondence": False,
            "mentions_churchill": False,
            "mentions_fairfax": False,
            "date_found": None,
            "relevance_score": 0
        }
        
        # Simple keyword matching - in a real implementation, use NLP
        churchill_patterns = [r'\bchurchill\b', r'\bwinston\b', r'\bprime\s+minister\b']
        fairfax_patterns = [r'\bfairfax\b', r'\bbryan\b', r'\bcolonel\b']
        date_pattern = r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(19[0-9]{2})'
        
        # Check for Churchill references
        for pattern in churchill_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                analysis["mentions_churchill"] = True
                analysis["relevance_score"] += 10
                break
        
        # Check for Fairfax references
        for pattern in fairfax_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                analysis["mentions_fairfax"] = True
                analysis["relevance_score"] += 10
                break
        
        # Look for dates
        date_matches = re.findall(date_pattern, text)
        if date_matches:
            # Parse the date - would need more robust handling in a real implementation
            try:
                day, month, year = date_matches[0]
                analysis["date_found"] = f"{day} {month} {year}"
                
                # Check if the date is in our target range (Oct-Dec 1946)
                month_mapping = {
                    "January": 1, "February": 2, "March": 3, "April": 4,
                    "May": 5, "June": 6, "July": 7, "August": 8,
                    "September": 9, "October": 10, "November": 11, "December": 12
                }
                
                if int(year) == 1946 and month_mapping.get(month, 0) >= 10:
                    analysis["relevance_score"] += 30
            except Exception as e:
                logger.error(f"Error parsing date: {str(e)}")
        
        # Determine if it's likely correspondence
        if analysis["mentions_churchill"] and analysis["mentions_fairfax"] and analysis["relevance_score"] >= 20:
            analysis["likely_correspondence"] = True
        
        return analysis


class FairfaxLetterAgent:
    """Agent to search for the original letter from Colonel Bryan Charles Fairfax to Winston Churchill."""
    
    def __init__(self):
        self.search_results = []
        self.most_likely_locations = []
        self.search_window_start = datetime(1946, 10, 1)  # Looking for letters from Oct-Nov 1946
        self.search_window_end = datetime(1946, 12, 5)    # Until Dec 5, 1946 (before Churchill's reply)
        
        # Initialize API clients for each archive
        self.api_clients = [ArchiveAPIClient(archive) for archive in ARCHIVES]
        
        # Initialize OCR processor
        self.ocr_processor = OCRProcessor()
        
        # Create download directory
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    def search_churchill_archives(self, query=None):
        """Search the Churchill Archives Centre at Churchill College, Cambridge."""
        logger.info(f"Searching Churchill Archives for: {query or 'Fairfax correspondence'}")
        
        # Find the Churchill Archives client
        churchill_client = next((client for client in self.api_clients 
                              if client.name == "Churchill Archives Centre"), None)
        
        if not churchill_client:
            logger.error("Churchill Archives client not initialized")
            return []
        
        # Construct search query
        if not query:
            query = "Fairfax correspondence"
        
        # Perform search with date parameters
        search_params = {
            "start_date": self.search_window_start,
            "end_date": self.search_window_end,
            "collection": "CHAR",  # Chartwell Papers
            "limit": 50
        }
        
        # Execute the search
        try:
            results = churchill_client.search(query, **search_params)
            
            if "error" in results:
                logger.error(f"Search error: {results['error']}")
                # Return empty list on error
                return []
            else:
                # Process real results
                possible_locations = []
                for item in results.get("results", []):
                    # Format would depend on actual API response
                    reference = item.get("reference", "Unknown")
                    title = item.get("title", "Untitled")
                    date = item.get("date", "")
                    possible_locations.append(f"{reference} - {title}, {date}")
                    
                    # Save document metadata for later retrieval
                    self.search_results.append({
                        "archive": "Churchill Archives Centre",
                        "reference": reference,
                        "title": title,
                        "date": date,
                        "item_id": item.get("id"),
                        "image_urls": item.get("images", [])
                    })
            
            logger.info(f"Found {len(possible_locations)} potential documents")
            self.most_likely_locations.extend(possible_locations)
            return possible_locations
            
        except Exception as e:
            logger.error(f"Error searching Churchill Archives: {str(e)}")
            # Return empty list on error
            return []
    
    def search_canadian_archives(self):
        """Search Canadian archives for Fairfax's copy or draft of the letter."""
        logger.info("Searching Canadian archives for Fairfax papers")
        
        # Get the Canadian archive clients
        lac_client = next((client for client in self.api_clients 
                        if client.name == "Library and Archives Canada"), None)
        toronto_client = next((client for client in self.api_clients 
                            if client.name == "University of Toronto Archives"), None)
        
        potential_sources = []
        
        # Search Library and Archives Canada
        if lac_client:
            logger.info("Searching Library and Archives Canada")
            search_params = {
                "start_date": self.search_window_start,
                "end_date": self.search_window_end,
                "limit": 30
            }
            
            # Try multiple search queries to maximize chances of finding relevant documents
            queries = [
                "Bryan Charles Fairfax Churchill",
                "Colonel Fairfax correspondence",
                "Fairfax Winston Churchill"
            ]
            
            for query in queries:
                try:
                    results = lac_client.search(query, **search_params)
                    
                    if "error" not in results:
                        for item in results.get("results", []):
                            # Format would depend on actual API response
                            reference = item.get("reference", "Unknown")
                            title = item.get("title", "Untitled")
                            date = item.get("date", "")
                            potential_sources.append(f"LAC: {reference} - {title}, {date}")
                            
                            # Save document metadata
                            self.search_results.append({
                                "archive": "Library and Archives Canada",
                                "reference": reference,
                                "title": title,
                                "date": date,
                                "item_id": item.get("id"),
                                "image_urls": item.get("images", [])
                            })
                except Exception as e:
                    logger.error(f"Error searching LAC with query '{query}': {str(e)}")
        
        # Search University of Toronto Archives
        if toronto_client:
            logger.info("Searching University of Toronto Archives")
            search_params = {
                "collection": "B1994-0002",  # Gooderham Family fonds
                "limit": 30
            }
            
            queries = [
                "Fairfax Churchill",
                "Bryan Charles Fairfax correspondence",
                "Fairfax Winston"
            ]
            
            for query in queries:
                try:
                    results = toronto_client.search(query, **search_params)
                    
                    if "error" not in results:
                        for item in results.get("results", []):
                            # Format would depend on actual API response
                            reference = item.get("reference", "Unknown")
                            title = item.get("title", "Untitled")
                            date = item.get("date", "")
                            potential_sources.append(f"UofT: {reference} - {title}, {date}")
                            
                            # Save document metadata
                            self.search_results.append({
                                "archive": "University of Toronto Archives",
                                "reference": reference,
                                "title": title,
                                "date": date,
                                "item_id": item.get("id"),
                                "image_urls": item.get("images", [])
                            })
                except Exception as e:
                    logger.error(f"Error searching UofT Archives with query '{query}': {str(e)}")
        
        # Log if no results were found
        if not potential_sources:
            logger.warning("No results found in Canadian archives")
        
        logger.info(f"Found {len(potential_sources)} potential sources in Canadian archives")
        self.most_likely_locations.extend(potential_sources)
        return potential_sources
    
    def download_documents(self, max_docs=5):
        """Download document images from search results for OCR processing."""
        logger.info(f"Starting document download process for up to {max_docs} documents")
        
        downloaded_docs = []
        download_count = 0
        
        # Prioritize documents from Oct-Nov 1946
        prioritized_results = sorted(
            self.search_results,
            key=lambda x: 0 if "1946" in x.get("date", "") and 
                        any(month in x.get("date", "") for month in ["Oct", "Nov", "December"]) else 1
        )
        
        for result in prioritized_results:
            if download_count >= max_docs:
                break
                
            # Get the archive client for this result
            archive_name = result.get("archive")
            client = next((c for c in self.api_clients if c.name == archive_name), None)
            
            if not client:
                logger.warning(f"No API client found for {archive_name}")
                continue
                
            # Get image URLs for this document
            image_urls = result.get("image_urls", [])
            if not image_urls:
                logger.info(f"No images available for {result.get('reference')}")
                continue
                
            # Create a folder for this document
            doc_id = result.get("item_id", "unknown")
            doc_ref = result.get("reference", "unknown").replace("/", "_")
            doc_folder = os.path.join(DOWNLOAD_DIR, f"{archive_name}_{doc_ref}")
            os.makedirs(doc_folder, exist_ok=True)
            
            # Download each image
            images_downloaded = []
            for i, url in enumerate(image_urls):
                output_path = os.path.join(doc_folder, f"page_{i+1}.jpg")
                success = client.download_document_image(url, output_path)
                
                if success:
                    images_downloaded.append(output_path)
            
            if images_downloaded:
                download_count += 1
                downloaded_docs.append({
                    "archive": archive_name,
                    "reference": result.get("reference"),
                    "title": result.get("title"),
                    "date": result.get("date"),
                    "images": images_downloaded
                })
                logger.info(f"Downloaded {len(images_downloaded)} images for {result.get('reference')}")
        
        logger.info(f"Download complete: {len(downloaded_docs)} documents with {sum(len(d['images']) for d in downloaded_docs)} total images")
        return downloaded_docs
    
    def process_ocr(self, downloaded_docs):
        """Process downloaded documents with OCR."""
        logger.info("Starting OCR processing of downloaded documents")
        
        ocr_results = []
        
        # Process each document
        for doc in downloaded_docs:
            doc_results = {
                "archive": doc["archive"],
                "reference": doc["reference"],
                "title": doc["title"],
                "date": doc["date"],
                "pages": [],
                "analysis": None
            }
            
            # Process each image in the document
            all_text = []
            for img_path in doc["images"]:
                text = self.ocr_processor.process_image(img_path)
                all_text.append(text)
                
                doc_results["pages"].append({
                    "image_path": img_path,
                    "text": text
                })
            
            # Analyze the combined text
            if all_text:
                combined_text = "\n\n".join(all_text)
                analysis = self.ocr_processor.analyze_text(combined_text)
                doc_results["analysis"] = analysis
                
                # Check if this might be the letter we're looking for
                if analysis["likely_correspondence"] and analysis["relevance_score"] > 30:
                    logger.info(f"Potential match found: {doc['reference']} (score: {analysis['relevance_score']})")
            
            ocr_results.append(doc_results)
        
        logger.info(f"OCR processing complete for {len(ocr_results)} documents")
        return ocr_results
    
    def extract_letter_content(self, ocr_results):
        """Extract potential letter content from OCR results."""
        logger.info("Analyzing OCR results for potential letter content")
        
        potential_letters = []
        
        for doc in ocr_results:
            analysis = doc.get("analysis")
            if not analysis or not analysis.get("likely_correspondence"):
                continue
                
            # Extract text of all pages
            all_text = "\n\n".join(page["text"] for page in doc.get("pages", []))
            
            # Basic extraction of letter format
            # This would be much more sophisticated in a real implementation
            lines = all_text.split("\n")
            letter_content = {}
            
            # Try to extract date, salutation, body, signature
            in_body = False
            body_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for date
                if not letter_content.get("date") and re.search(r'\d{1,2}\s+\w+\s+19\d{2}', line):
                    letter_content["date"] = line
                
                # Look for salutation (Dear...)
                elif not letter_content.get("salutation") and line.startswith("Dear"):
                    letter_content["salutation"] = line
                    in_body = True
                
                # Look for signature (usually at the end)
                elif in_body and ("Sincerely" in line or "Yours" in line):
                    letter_content["signature"] = line
                    in_body = False
                
                # Collect body lines
                elif in_body:
                    body_lines.append(line)
            
            # Set body content
            if body_lines:
                letter_content["body"] = "\n".join(body_lines)
                
            # Only include if we found some structure
            if len(letter_content) >= 2:
                potential_letters.append({
                    "archive": doc["archive"],
                    "reference": doc["reference"],
                    "title": doc["title"],
                    "date": doc["date"],
                    "extracted_content": letter_content,
                    "relevance_score": analysis.get("relevance_score", 0),
                    "full_text": all_text
                })
        
        # Sort by relevance score
        potential_letters.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.info(f"Found {len(potential_letters)} potential letters")
        return potential_letters
    
    def construct_likely_content(self):
        """Construct likely content of Fairfax's letter based on historical context."""
        likely_topics = [
            "Reflections on Churchill's 'Iron Curtain' speech (March 1946)",
            "Comments on Churchill's opposition leadership in Parliament",
            "Shared memories from military service",
            "Discussion of post-war international relations",
            "Possible mention of Churchill's upcoming history of WWII",
            "News of Toronto social and political circles",
            "Personal reflections on Fairfax's military career and Churchill's leadership"
        ]
        
        logger.info("Analyzing likely letter content based on historical context")
        for topic in likely_topics:
            logger.info(f"Potential topic: {topic}")
        
        return likely_topics
    
    def generate_search_plan(self):
        """Generate a comprehensive search plan for finding the letter."""
        plan = {
            "primary_archives": [
                {
                    "name": "Churchill Archives Centre",
                    "location": "Churchill College, Cambridge, UK",
                    "collections": ["CHAR (Chartwell Papers)", "CHUR (Churchill Papers)"],
                    "contact": "archives@chu.cam.ac.uk",
                    "request_procedure": "Email with specific reference numbers and research purpose"
                },
                {
                    "name": "University of Toronto Archives",
                    "location": "Toronto, Canada",
                    "collections": ["Gooderham Family fonds", "Fairfax family papers"],
                    "contact": "utarms@utoronto.ca"
                },
                {
                    "name": "Library and Archives Canada",
                    "location": "Ottawa, Canada",
                    "collections": ["Military Personnel Records", "Canadian Expeditionary Force"]
                }
            ],
            "search_strategy": [
                "Query Churchill Archives CALM catalogue for correspondence from Fairfax, Oct-Dec 1946",
                "Request specific CHAR files containing personal correspondence from this period",
                "Search Canadian archives for Fairfax's personal papers or letter copies",
                "Contact Fairfax/Gooderham family descendants for private collections",
                "Search newspaper archives for any mention of communication between the two"
            ],
            "search_terms": [
                "Fairfax, Bryan Charles",
                "Colonel Fairfax",
                "Fairfax + Churchill + 1946",
                "Canadian Battalion + Churchill + correspondence",
                "Gooderham + Churchill"
            ],
            "api_access_requirements": [
                "Churchill Archives Centre requires registration and API key",
                "Library and Archives Canada requires institutional access",
                "University of Toronto Archives requires research request approval"
            ],
            "ocr_process": [
                "Download document images from archive APIs",
                "Process images with OCR to extract text",
                "Analyze text for relevance to Fairfax-Churchill correspondence",
                "Extract letter components (date, salutation, body, signature)",
                "Validate letter content against historical context"
            ]
        }
        
        return plan
        
    def execute_full_search(self):
        """Execute a complete search for the Fairfax letter including OCR processing."""
        logger.info("===== BEGINNING COMPREHENSIVE SEARCH FOR FAIRFAX LETTER =====")
        
        # Step 1: Search archives
        logger.info("Step 1: Searching archives for potential documents")
        churchill_results = self.search_churchill_archives("Fairfax Winston Churchill correspondence")
        canadian_results = self.search_canadian_archives()
        
        if not self.search_results:
            logger.error("No results found in any archives")
            return {"status": "failure", "reason": "No search results found"}
            
        # Step 2: Download documents for OCR processing
        logger.info("Step 2: Downloading documents for OCR processing")
        downloaded_docs = self.download_documents(max_docs=10)
        
        if not downloaded_docs:
            logger.error("Failed to download any documents")
            return {
                "status": "partial",
                "search_results": self.search_results,
                "reason": "No documents could be downloaded"
            }
            
        # Step 3: Process documents with OCR
        logger.info("Step 3: Processing documents with OCR")
        ocr_results = self.process_ocr(downloaded_docs)
        
        # Step 4: Extract potential letter content
        logger.info("Step 4: Extracting potential letter content")
        potential_letters = self.extract_letter_content(ocr_results)
        
        # Step 5: Generate search plan for further investigation
        logger.info("Step 5: Generating comprehensive search plan")
        search_plan = self.generate_search_plan()
        
        # Step 6: Construct likely letter content based on historical context
        logger.info("Step 6: Constructing likely letter content based on historical context")
        likely_content = self.construct_likely_content()
        
        # Prepare final results
        results = {
            "status": "success" if potential_letters else "partial",
            "potential_letters_found": len(potential_letters),
            "top_matches": potential_letters[:3] if potential_letters else [],
            "search_results_count": len(self.search_results),
            "documents_processed": len(ocr_results),
            "search_plan": search_plan,
            "most_likely_locations": self.most_likely_locations
        }
        
        logger.info(f"===== SEARCH COMPLETE: {results['status'].upper()} =====")
        
        if results["status"] == "success":
            logger.info(f"Found {len(potential_letters)} potential matches for the Fairfax letter")
        else:
            logger.info("No definitive match found for the Fairfax letter")
            
        return results

def main():
    parser = argparse.ArgumentParser(description='Search for the original Fairfax letter to Churchill')
    parser.add_argument('--query', help='Additional search terms')
    parser.add_argument('--period', help='Time period to search (format: YYYY-MM to YYYY-MM)')
    parser.add_argument('--full', action='store_true', help='Run full search including OCR processing')
    parser.add_argument('--ocr-only', help='Run OCR on previously downloaded documents in the specified directory')
    parser.add_argument('--max-docs', type=int, default=5, help='Maximum number of documents to download (default: 5)')
    args = parser.parse_args()
    
    agent = FairfaxLetterAgent()
    
    logger.info("\n" + "=" * 80)
    logger.info("FAIRFAX LETTER FINDER AGENT")
    logger.info("Searching for the original letter from Colonel Bryan Charles Fairfax, C.M.G.")
    logger.info("to Winston Churchill (likely written November 1946)")
    logger.info("=" * 80)
    
    if args.ocr_only or args.full:
        # Check if OCR dependencies are available
        if not HAS_PIL or not HAS_TESSERACT:
            logger.error("OCR dependencies are missing. Please install required packages:")
            logger.error("pip install -r requirements.txt")
            logger.error("And ensure Tesseract OCR is installed on your system.")
            logger.error("See: https://github.com/tesseract-ocr/tesseract")
            return
            
    if args.ocr_only:
        # Only run OCR on previously downloaded documents
        if not os.path.isdir(args.ocr_only):
            logger.error(f"Directory not found: {args.ocr_only}")
            return
        
        logger.info(f"Running OCR on documents in {args.ocr_only}")
        
        # Construct document list from directory
        downloaded_docs = []
        for root, dirs, files in os.walk(args.ocr_only):
            image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
            if image_files:
                dir_name = os.path.basename(root)
                downloaded_docs.append({
                    "archive": "unknown",
                    "reference": dir_name,
                    "title": dir_name,
                    "date": "",
                    "images": [os.path.join(root, f) for f in image_files]
                })
        
        if not downloaded_docs:
            logger.error(f"No image files found in {args.ocr_only}")
            return
        
        # Process with OCR
        ocr_results = agent.process_ocr(downloaded_docs)
        potential_letters = agent.extract_letter_content(ocr_results)
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("OCR PROCESSING RESULTS")
        logger.info("=" * 80)
        
        logger.info(f"\nProcessed {len(downloaded_docs)} documents with {sum(len(d['images']) for d in downloaded_docs)} images")
        logger.info(f"Found {len(potential_letters)} potential letter matches")
        
        for i, letter in enumerate(potential_letters, 1):
            logger.info(f"\nPotential Letter {i} (Score: {letter['relevance_score']})")
            logger.info(f"Archive: {letter['archive']}")
            logger.info(f"Reference: {letter['reference']}")
            
            content = letter["extracted_content"]
            if "date" in content:
                logger.info(f"Date: {content['date']}")
            if "salutation" in content:
                logger.info(f"Salutation: {content['salutation']}")
            if "body" in content:
                logger.info(f"Body excerpt: {content['body'][:100]}...")
                
        return
    
    elif args.full:
        # Execute full search pipeline including OCR
        logger.info("Executing full search pipeline including OCR processing")
        results = agent.execute_full_search()
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("FULL SEARCH RESULTS")
        logger.info("=" * 80)
        
        logger.info(f"\nSearch status: {results['status']}")
        logger.info(f"Documents found: {results['search_results_count']}")
        logger.info(f"Documents processed with OCR: {results['documents_processed']}")
        logger.info(f"Potential letter matches: {results['potential_letters_found']}")
        
        if results["top_matches"]:
            logger.info("\nTop potential matches:")
            for i, match in enumerate(results["top_matches"], 1):
                logger.info(f"\nMatch {i} (Score: {match['relevance_score']})")
                logger.info(f"Archive: {match['archive']}")
                logger.info(f"Reference: {match['reference']}")
                logger.info(f"Title: {match['title']}")
                logger.info(f"Date: {match['date']}")
                
                content = match["extracted_content"]
                if "salutation" in content:
                    logger.info(f"Salutation: {content['salutation']}")
                if "body" in content:
                    body_excerpt = content["body"][:150] + "..." if len(content["body"]) > 150 else content["body"]
                    logger.info(f"Body excerpt: {body_excerpt}")
    
    else:
        # Run basic search without OCR
        logger.info("Running basic search without OCR processing")
        
        # Search archives
        logger.info("\n[1] Searching Churchill Archives Centre...")
        churchill_results = agent.search_churchill_archives(args.query)
        
        logger.info("\n[2] Searching Canadian Archives...")
        canadian_results = agent.search_canadian_archives()
        
        # Generate content hypothesis
        logger.info("\n[3] Analyzing possible letter content...")
        likely_content = agent.construct_likely_content()
        
        # Create search plan
        logger.info("\n[4] Generating comprehensive search plan...")
        search_plan = agent.generate_search_plan()
        
        logger.info("\n" + "=" * 80)
        logger.info("SEARCH RESULTS SUMMARY")
        logger.info("=" * 80)
        
        logger.info("\nMost likely locations for Fairfax's original letter:")
        for i, location in enumerate(agent.most_likely_locations, 1):
            logger.info(f"{i}. {location}")
        
        logger.info("\nNext steps for archival research:")
        for i, step in enumerate(search_plan["search_strategy"], 1):
            logger.info(f"{i}. {step}")
        
        logger.info("\nOCR processing capabilities:")
        for i, step in enumerate(search_plan["ocr_process"], 1):
            logger.info(f"{i}. {step}")
        
        logger.info("\nTo execute full search with OCR processing, run:")
        logger.info("python fairfax_letter_finder.py --full")
        
    logger.info("\n===== REAL-WORLD ARCHIVE ACCESS INFORMATION =====")
    logger.info("This agent attempts to connect to actual archives, but most require formal access:")
    logger.info("")
    logger.info("1. Churchill Archives Centre:")
    logger.info("   - Requires reader's ticket application: https://archives.chu.cam.ac.uk/researchers")
    logger.info("   - Commercial access via subscription: https://www.churchillarchive.com/")
    logger.info("   - Email for research inquiries: archives@chu.cam.ac.uk")
    logger.info("")
    logger.info("2. Library and Archives Canada:")
    logger.info("   - Access request form: https://www.bac-lac.gc.ca/eng/services/access-request/Pages/access-request.aspx")
    logger.info("   - Email: bac.reference.lac@canada.ca")
    logger.info("")
    logger.info("3. University of Toronto Archives:")
    logger.info("   - Research appointment form: https://utarms.library.utoronto.ca/contact-us")
    logger.info("   - Email: utarms@utoronto.ca")
    logger.info("")
    logger.info("For best results, researchers should:")
    logger.info("1. Contact archives directly with specific reference numbers")
    logger.info("2. Explain your research purpose and request access to Fairfax correspondence")
    logger.info("3. Ask specifically about letters between Colonel Bryan Fairfax and Churchill from late 1946")

if __name__ == "__main__":
    main()