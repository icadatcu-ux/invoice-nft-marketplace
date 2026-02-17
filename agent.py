import os
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from web3 import Web3
import PyPDF2

def _load_env():
    """Load environment variables from .env file"""
    load_dotenv(override=False)
    script_dir = Path(__file__).resolve().parent
    
    for filename in (".env", ".env.txt"):
        p = script_dir / filename
        if p.exists():
            load_dotenv(dotenv_path=p, override=False)
    
    # Default RPC if not set
    os.environ.setdefault("BSC_TESTNET_RPC", "https://data-seed-prebsc-1-s1.binance.org:8545/")

# Load environment variables
_load_env()

# Configure Gemini AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

# Web3 setup for BSC Testnet
w3 = Web3(Web3.HTTPProvider(os.getenv('BSC_TESTNET_RPC')))

# Smart contract setup - DEPLOYED ON BSC TESTNET
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS', '0xfde796D7E133A61636eD51f1e2F145C35b28617b')

# Full ABI from Remix compilation
CONTRACT_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "invoiceHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "registrar", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "metadata", "type": "string"}
        ],
        "name": "InvoiceRegistered",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_invoiceHash", "type": "bytes32"},
            {"internalType": "string", "name": "_metadata", "type": "string"}
        ],
        "name": "registerInvoice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_invoiceHash", "type": "bytes32"}],
        "name": "getInvoice",
        "outputs": [
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "registrar", "type": "address"},
            {"internalType": "string", "name": "metadata", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "invoices",
        "outputs": [
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "registrar", "type": "address"},
            {"internalType": "string", "name": "metadata", "type": "string"},
            {"internalType": "bool", "name": "exists", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_invoiceHash", "type": "bytes32"}],
        "name": "verifyInvoice",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class InvoiceAgent:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        print("Invoice Verification Agent initialized")
        print(f"Mode: {'MOCK (no blockchain)' if mock_mode else 'LIVE (blockchain active)'}")
        
        if not mock_mode:
            print(f"Contract: {CONTRACT_ADDRESS}")
            print(f"Network: BSC Testnet")
            
            # Verify connection
            if w3.is_connected():
                print(f"✓ Connected to BSC Testnet")
                private_key = os.getenv('WALLET_PRIVATE_KEY')
                if private_key:
                    account = w3.eth.account.from_key(private_key)
                    balance = w3.eth.get_balance(account.address)
                    print(f"✓ Wallet: {account.address}")
                    print(f"✓ Balance: {w3.from_wei(balance, 'ether')} tBNB")
                else:
                    print("⚠ Warning: WALLET_PRIVATE_KEY not set in .env")
            else:
                print("✗ Failed to connect to BSC Testnet")
        
    def analyze_invoice_locally(self, invoice_text):
        """Heuristic/offline fallback when AI is unavailable"""
        text = invoice_text or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        def first_match(patterns):
            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
                if m:
                    return (m.group(1) or "").strip()
            return None

        invoice_number = first_match([
            r"(?:invoice\s*(?:number|no\.?|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
            r"(?:inv(?:oice)?\s*#\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
        ])

        date = first_match([
            r"(?:date\s*[:\-]?\s*)(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
            r"(?:date\s*[:\-]?\s*)(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ])

        total_line = None
        for ln in lines:
            if re.search(r"\btotal\b", ln, flags=re.IGNORECASE):
                total_line = ln
                break

        currency = None
        total_amount = None
        if total_line:
            m_cur = re.search(r"\b(EUR|USD|GBP|RON|LEI|CHF|CAD|AUD|JPY)\b", total_line, flags=re.IGNORECASE)
            if m_cur:
                currency = m_cur.group(1).upper()
            m_amt = re.search(r"([0-9]{1,3}(?:[ ,][0-9]{3})*(?:[.,][0-9]{2})?)", total_line)
            if m_amt:
                total_amount = m_amt.group(1).replace(" ", "")

        supplier_name = lines[0] if lines else None

        potential_issues = []
        if not invoice_number:
            potential_issues.append("Could not extract invoice number (offline parsing).")
        if not date:
            potential_issues.append("Could not extract date (offline parsing).")
        if not total_amount:
            potential_issues.append("Could not extract total amount (offline parsing).")

        return {
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "date": date,
            "total_amount": total_amount,
            "currency": currency,
            "vat_amount": None,
            "line_items": [],
            "potential_issues": potential_issues,
        }

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF invoice"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def analyze_invoice_with_ai(self, invoice_text):
        """Use Gemini AI to extract structured data from invoice"""
        prompt = f"""
        Analyze this invoice and extract the following information in JSON format:
        - supplier_name
        - invoice_number
        - date
        - total_amount
        - currency
        - vat_amount
        - line_items (array of {{description, quantity, unit_price, total}})
        - potential_issues (array of any anomalies like: duplicate invoice numbers, unusual amounts, missing VAT, incorrect calculations)
        
        Invoice text:
        {invoice_text}
        
        Return ONLY valid JSON, no additional text.
        """
        
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            
            return json.loads(result)
        except Exception as e:
            fallback = self.analyze_invoice_locally(invoice_text)
            msg = str(e).replace("\n", " ").strip()
            msg = (msg[:160] + "...") if len(msg) > 160 else msg
            fallback.setdefault("potential_issues", [])
            fallback["potential_issues"].insert(0, f"AI unavailable; used offline parsing. ({type(e).__name__}: {msg})")
            return fallback
    
    def calculate_hash(self, invoice_text):
        """Calculate SHA-256 hash of invoice"""
        return hashlib.sha256(invoice_text.encode()).hexdigest()
    
    def register_onchain(self, invoice_hash, metadata):
        """Register invoice hash on BSC blockchain"""
        if self.mock_mode:
            # Mock blockchain registration
            mock_tx_hash = f"0x{''.join([format(ord(c), 'x') for c in invoice_hash[:32]])}"
            print("\n🔷 MOCK TRANSACTION")
            print(f"   Hash: {mock_tx_hash}")
            print(f"   Network: BSC Testnet (SIMULATED)")
            print(f"   Explorer: https://testnet.bscscan.com/tx/{mock_tx_hash}")
            return mock_tx_hash
        
        try:
            # Real blockchain transaction
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            if not private_key:
                print("\n✗ Error: WALLET_PRIVATE_KEY not set in .env file")
                return None
                
            account = w3.eth.account.from_key(private_key)
            contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
            
            # Convert hash to bytes32 (remove 0x if present, pad/trim to 32 bytes)
            clean_hash = invoice_hash.replace('0x', '')
            if len(clean_hash) > 64:
                clean_hash = clean_hash[:64]
            hash_bytes = bytes.fromhex(clean_hash)
            
            # Check if invoice already registered
            try:
                already_registered = contract.functions.verifyInvoice(hash_bytes).call()
                if already_registered:
                    print(f"\n⚠️  WARNING: Invoice already registered on blockchain!")
                    print(f"   Hash: {invoice_hash}")
                    print(f"   Try with a different invoice to test.")
                    return None
            except Exception as check_err:
                # If check fails, continue anyway (contract might not have this function)
                pass
            
            # Estimate gas dynamically
            try:
                gas_estimate = contract.functions.registerInvoice(
                    hash_bytes,
                    json.dumps(metadata)
                ).estimate_gas({'from': account.address})
                
                gas_limit = int(gas_estimate * 1.5)  # Add 50% buffer
                print(f"   Estimated gas: {gas_estimate}, using: {gas_limit}")
            except Exception as gas_err:
                # If estimation fails, use high default
                gas_limit = 500000
                print(f"⚠️  Gas estimation failed: {gas_err}")
                print(f"   Using default gas limit: {gas_limit}")
            
            # Build transaction
            txn = contract.functions.registerInvoice(
                hash_bytes,
                json.dumps(metadata)
            ).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': gas_limit,
                'gasPrice': w3.eth.gas_price
            })
            
            # Sign and send
            print("\n🔄 Signing transaction...")
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            
            print("📤 Broadcasting to BSC Testnet...")
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print("\n✅ REAL TRANSACTION SENT!")
            print(f"   Hash: {tx_hash.hex()}")
            print(f"   Explorer: https://testnet.bscscan.com/tx/{tx_hash.hex()}")
            print(f"   Waiting for confirmation...")
            
            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"✅ Transaction confirmed in block {receipt['blockNumber']}")
            else:
                print(f"✗ Transaction failed")
            
            return tx_hash.hex()
            
        except Exception as e:
            print(f"\n✗ Blockchain error: {str(e)}")
            return None
    
    def process_invoice(self, invoice_path):
        """Main function to process invoice end-to-end"""
        print(f"\n{'='*60}")
        print(f"Processing Invoice: {os.path.basename(invoice_path)}")
        print(f"{'='*60}")
        
        # Step 1: Extract text
        print("\n[1/4] Extracting text from invoice...")
        invoice_text = self.extract_text_from_pdf(invoice_path)
        if "Error" in invoice_text:
            print(f"✗ ERROR: {invoice_text}")
            return
        print(f"✓ Extracted {len(invoice_text)} characters")
        
        # Step 2: AI Analysis
        print("\n[2/4] Analyzing with AI...")
        analysis = self.analyze_invoice_with_ai(invoice_text)
        
        if "error" in analysis:
            print(f"✗ ERROR: {analysis['error']}")
            return
        
        print("✓ Analysis complete:")
        print(f"   Supplier: {analysis.get('supplier_name', 'N/A')}")
        print(f"   Invoice #: {analysis.get('invoice_number', 'N/A')}")
        print(f"   Date: {analysis.get('date', 'N/A')}")
        print(f"   Total: {analysis.get('total_amount', 'N/A')} {analysis.get('currency', '')}")
        
        if analysis.get('potential_issues'):
            print("\n⚠ Potential Issues:")
            for issue in analysis['potential_issues']:
                print(f"   - {issue}")
        
        # Step 3: Calculate hash
        print("\n[3/4] Calculating document hash...")
        doc_hash = self.calculate_hash(invoice_text)
        print(f"✓ Hash: {doc_hash[:16]}...{doc_hash[-16:]}")
        
        # Step 4: Register onchain
        print("\n[4/4] Registering on blockchain...")
        metadata = {
            "supplier": analysis.get('supplier_name'),
            "invoice_number": analysis.get('invoice_number'),
            "total": analysis.get('total_amount'),
            "timestamp": datetime.now().isoformat()
        }
        
        tx_hash = self.register_onchain(doc_hash, metadata)
        
        if tx_hash:
            print(f"\n{'='*60}")
            print("✅ SUCCESS! Invoice verified and registered")
            print(f"{'='*60}")
            
            # Save results
            result = {
                "invoice_file": os.path.basename(invoice_path),
                "document_hash": doc_hash,
                "transaction_hash": tx_hash,
                "contract_address": CONTRACT_ADDRESS if not self.mock_mode else "MOCK_MODE",
                "network": "BSC Testnet",
                "analysis": analysis,
                "timestamp": datetime.now().isoformat(),
                "mode": "LIVE" if not self.mock_mode else "MOCK"
            }
            
            result_file = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\n📄 Full results saved to: {result_file}")
            return result
        
        return None

if __name__ == "__main__":
    import sys
    
    # Initialize agent in mock mode by default
    agent = InvoiceAgent(mock_mode=True)
    
    if len(sys.argv) < 2:
        print("\nUsage: python agent.py <path_to_invoice.pdf>")
        print("   Example: python agent.py sample_invoice.pdf")
        print("\n   Add --live flag to use real blockchain")
        print("   python agent.py sample_invoice.pdf --live")
        sys.exit(1)
    
    # Check for live mode flag
    if "--live" in sys.argv:
        agent.mock_mode = False
        sys.argv.remove("--live")
    
    invoice_path = sys.argv[1]

    # Handle missing .pdf extension
    if not os.path.exists(invoice_path):
        candidates = []
        if not invoice_path.lower().endswith(".pdf"):
            candidates.append(f"{invoice_path}.pdf")
        candidates.append(f"{invoice_path}.pdf")
        for cand in candidates:
            if cand != invoice_path and os.path.exists(cand):
                invoice_path = cand
                break
    
    if not os.path.exists(invoice_path):
        print(f"✗ Error: File not found: {invoice_path}")
        sys.exit(1)
    
    # Process the invoice
    agent.process_invoice(invoice_path)
