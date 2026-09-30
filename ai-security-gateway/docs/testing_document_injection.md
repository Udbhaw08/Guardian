# Testing Document Upload Injection (PDF/Image)

This guide explains how to test the AI Security Gateway's ability to detect hidden prompt injections embedded inside documents (PDFs and Images).

Attackers often hide malicious instructions inside uploaded files using stealth techniques like:
- **Tiny Font Size** (e.g., 1.5pt, invisible to the human eye but readable by AI)
- **White-on-White Text** (blends into the background)
- **Low Opacity / Transparent Text**
- **Off-page Coordinates**

Our system catches this by extracting the text, analyzing the metadata (font size, color, etc.), and running it through our trained Machine Learning classifier.

---

## 1. Prerequisites (For Image OCR)

While PDFs can be parsed natively by our system (using PyMuPDF), scanning **Images (PNG, JPG, etc.)** requires an OCR (Optical Character Recognition) engine installed on your computer.

We use **Tesseract OCR**. You must install the binary for the image scanner to work:

### Windows Installation:
1. Download the installer from the official UB-Mannheim GitHub wiki:
   👉 **[Download Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)**
2. Run the installer (e.g., `tesseract-ocr-w64-setup-5.3.3.xxx.exe`).
3. **CRITICAL:** Make sure Tesseract is added to your system `PATH` during installation, or you will get a "Tesseract not found" error when scanning images.
4. Restart your terminal/computer after installing.

*(Note: Mac users can simply run `brew install tesseract`, Linux users can run `sudo apt install tesseract-ocr`)*

---


## 2. How to Test via ChatGPT

If you have connected the Gateway to ChatGPT (via Ngrok) as an MCP tool:

1. Start your `uvicorn` server and your `ngrok` tunnel.
2. Start a new chat in ChatGPT.
3. Attach the `sample.pdf` file to the chat.
4. Use this exact prompt to trigger our security scan:
   > Please use the `scan_document` tool to analyze this file.

