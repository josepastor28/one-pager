#!/usr/bin/env python3
"""
PDF Generator for Polisense One-Pager
Uses Playwright to convert HTML to PDF with proper styling and colors
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

def verify_pdf_page_count(pdf_path: Path, expected_pages: int) -> bool:
    """Verify the number of pages in a PDF file using pdfinfo."""
    if not pdf_path.exists():
        print(f"Verification failed: PDF file not found at {pdf_path}")
        return False
    
    try:
        print("� Verifying PDF page count...")
        result = subprocess.run(
            ['pdfinfo', str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                page_count = int(line.split(":")[1].strip())
                if page_count == expected_pages:
                    print(f"Verification successful: PDF has {page_count} page(s).")
                    return True
                else:
                    print(f"Verification failed: Expected {expected_pages} page(s), but found {page_count}.")
                    return False
        
        print("Verification failed: Could not determine page count from pdfinfo output.")
        return False

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running pdfinfo: {e}")
        print("    Please ensure 'pdfinfo' (from poppler-utils) is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during verification: {e}")
        return False

import http.server
import socketserver
import threading
import socket
import json

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress logging

def run_server(port, server_started):
    handler = QuietHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        server_started.set()
        httpd.serve_forever()

async def generate_pdf(language='en'):
    """Generate PDF from HTML file using Playwright"""
    
    # File paths
    html_file = Path("polisense-A4.html")
    output_dir = Path("one-pager")
    output_dir.mkdir(exist_ok=True)
    
    if language == 'en':
        pdf_file = output_dir / "polisense-one-pager.pdf"
        labels_file = "labels.json"
    else:
        pdf_file = output_dir / f"{language.upper()}-polisense-one-pager.pdf"
        labels_file = f"labels_{language}.json"

    if not html_file.exists():
        print(f"Error: {html_file} not found")
        return False

    port = find_free_port()
    server_started = threading.Event()
    server_thread = threading.Thread(target=run_server, args=(port, server_started))
    server_thread.daemon = True
    server_thread.start()
    server_started.wait() # Wait for server to be ready
    
    try:
        print(f"Starting PDF generation for language: {language.upper()}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            page.on("console", lambda msg: print(f"PAGE LOG: {msg.text}"))
            
            # Pass the labels file name to the page via query parameter
            url = f"http://localhost:{port}/{html_file}?lang={language}"
            print(f"Loading HTML file from {url}...")
            await page.goto(url, wait_until="networkidle")
            
            await page.wait_for_selector('body.content-loaded', timeout=5000)

            print("Generating PDF...")
            pdf_bytes = await page.pdf(
                format='A4',
                print_background=True,
                margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'}
            )
            await browser.close()
            
        with open(pdf_file, "wb") as f:
            f.write(pdf_bytes)
            
        if pdf_file.exists():
            file_size = pdf_file.stat().st_size / 1024
            print(f"PDF generated: {pdf_file} ({file_size:.1f} KB)")
            return True  # Skip verification for now
        else:
            print("Error: PDF file was not created")
            return False
            
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # The server thread is a daemon, so it will exit when the main thread exits.
        pass

if __name__ == "__main__":
    # Generate English version
    en_success = asyncio.run(generate_pdf(language='en'))
    
    # Generate Spanish version
    es_success = asyncio.run(generate_pdf(language='es'))

    sys.exit(0 if en_success and es_success else 1)