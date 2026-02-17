import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from web3 import Web3
import google.generativeai as genai

load_dotenv()

# Web3 setup
w3 = Web3(Web3.HTTPProvider(os.getenv('BSC_TESTNET_RPC', 'https://data-seed-prebsc-1-s1.binance.org:8545/')))

# Configure AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

# Smart contract (will be deployed)
NFT_CONTRACT_ADDRESS = os.getenv('NFT_CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000')

NFT_CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "_documentHash", "type": "bytes32"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_dueDate", "type": "uint256"},
            {"name": "_riskScore", "type": "uint8"},
            {"name": "_metadata", "type": "string"}
        ],
        "name": "mintInvoice",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "_tokenId", "type": "uint256"},
            {"name": "_price", "type": "uint256"}
        ],
        "name": "listInvoice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "_tokenId", "type": "uint256"}],
        "name": "calculateRecommendedPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "_tokenId", "type": "uint256"}],
        "name": "getInvoice",
        "outputs": [
            {"name": "documentHash", "type": "bytes32"},
            {"name": "amount", "type": "uint256"},
            {"name": "dueDate", "type": "uint256"},
            {"name": "supplier", "type": "address"},
            {"name": "currentOwner", "type": "address"},
            {"name": "isRedeemed", "type": "bool"},
            {"name": "listedPrice", "type": "uint256"},
            {"name": "riskScore", "type": "uint8"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class InvoiceTokenizationAgent:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        print("Invoice Tokenization Agent initialized")
        print(f"Mode: {'MOCK' if mock_mode else 'LIVE (NFT minting active)'}")
        
        if not mock_mode and w3.is_connected():
            print(f"✓ Connected to BSC Testnet")
            
    def calculate_ai_pricing(self, invoice_data, fraud_score):
        """
        Use AI to calculate optimal pricing for invoice sale
        Considers: amount, due date, fraud risk, market conditions
        """
        
        # Extract key data
        total_amount = invoice_data.get('total_amount', '0')
        
        # Handle both string and numeric types
        if isinstance(total_amount, (int, float)):
            amount = float(total_amount)
        else:
            # String type - clean it
            amount_str = str(total_amount).replace('$', '').replace(',', '').strip()
            try:
                amount = float(amount_str)
            except:
                amount = 0
        
        due_date = invoice_data.get('date', 'unknown')
        supplier = invoice_data.get('supplier_name', 'unknown')
        
        prompt = f"""
        You are an AI pricing agent for an invoice financing marketplace.
        
        Invoice Details:
        - Amount: ${amount}
        - Due Date: {due_date}
        - Supplier: {supplier}
        - Fraud Risk Score: {fraud_score}/100 (0=safe, 100=high risk)
        
        Calculate optimal pricing for early payment:
        1. Time discount: How much discount for paying before due date?
        2. Risk premium: Additional discount for fraud risk?
        3. Market rate: Typical invoice financing is 1-5% discount per month
        
        Return JSON with:
        {{
            "recommended_price": <dollar amount>,
            "discount_percentage": <percentage>,
            "confidence": <0-100>,
            "reasoning": "<brief explanation>"
        }}
        
        Return ONLY valid JSON, no additional text.
        """
        
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            
            # Clean response
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            
            pricing = json.loads(result)
            return pricing
            
        except Exception as e:
            # Fallback pricing algorithm
            print(f"⚠️  AI pricing failed: {e}")
            return self._fallback_pricing(amount, fraud_score)
    
    def _fallback_pricing(self, amount, fraud_score):
        """Simple rule-based pricing when AI fails"""
        # Base discount: 2%
        base_discount = 2.0
        
        # Risk premium: 0-5% based on fraud score
        risk_premium = (fraud_score / 100) * 5.0
        
        total_discount = base_discount + risk_premium
        recommended_price = amount * (1 - total_discount / 100)
        
        return {
            "recommended_price": round(recommended_price, 2),
            "discount_percentage": round(total_discount, 2),
            "confidence": 60,
            "reasoning": "Fallback pricing: 2% base + risk premium"
        }
    
    def tokenize_invoice(self, invoice_hash, invoice_data, fraud_score):
        """
        Mint invoice as NFT on blockchain
        """
        print("\n" + "="*60)
        print("TOKENIZING INVOICE AS NFT")
        print("="*60)
        
        # Parse invoice amount (convert to smallest unit - cents)
        total_amount = invoice_data.get('total_amount', '0')
        
        # Handle both string and numeric types
        if isinstance(total_amount, (int, float)):
            amount_dollars = float(total_amount)
        else:
            # String type - clean it
            amount_str = str(total_amount).replace('$', '').replace(',', '').strip()
            try:
                amount_dollars = float(amount_str)
            except:
                print("❌ Invalid amount format")
                return None
        
        amount_cents = int(amount_dollars * 100)
        
        # Calculate due date (assume 30 days if not specified)
        due_date_timestamp = int((datetime.now() + timedelta(days=30)).timestamp())
        
        # Get AI pricing
        print("\n[1/3] Calculating optimal pricing with AI...")
        pricing = self.calculate_ai_pricing(invoice_data, fraud_score)
        print(f"✓ Recommended price: ${pricing['recommended_price']}")
        print(f"  Discount: {pricing['discount_percentage']}%")
        print(f"  Reasoning: {pricing['reasoning']}")
        
        # Prepare metadata
        metadata = {
            "supplier": invoice_data.get('supplier_name'),
            "invoice_number": invoice_data.get('invoice_number'),
            "original_amount": amount_dollars,
            "recommended_price": pricing['recommended_price'],
            "fraud_score": fraud_score,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.mock_mode:
            # Mock tokenization
            mock_token_id = hash(invoice_hash) % 100000
            print(f"\n[2/3] MOCK: Minting NFT...")
            print(f"✓ Token ID: #{mock_token_id}")
            print(f"✓ Contract: {NFT_CONTRACT_ADDRESS} (MOCK)")
            print(f"✓ Face Value: ${amount_dollars}")
            print(f"✓ Recommended Listing: ${pricing['recommended_price']}")
            
            print(f"\n[3/3] MOCK: Listing on marketplace...")
            print(f"✓ Listed at ${pricing['recommended_price']}")
            print(f"✓ Savings for buyer: ${amount_dollars - pricing['recommended_price']:.2f}")
            
            return {
                "success": True,
                "token_id": mock_token_id,
                "face_value": amount_dollars,
                "listed_price": pricing['recommended_price'],
                "discount": pricing['discount_percentage'],
                "mode": "MOCK"
            }
        
        try:
            # Real blockchain minting
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            if not private_key:
                print("❌ WALLET_PRIVATE_KEY not set")
                return None
            
            account = w3.eth.account.from_key(private_key)
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS),
                abi=NFT_CONTRACT_ABI
            )
            
            # Convert hash to bytes32
            hash_bytes = bytes.fromhex(invoice_hash.replace('0x', '')[:64])
            
            print(f"\n[2/3] Minting NFT on blockchain...")
            
            # Build transaction
            txn = contract.functions.mintInvoice(
                hash_bytes,
                amount_cents,
                due_date_timestamp,
                fraud_score,
                json.dumps(metadata)
            ).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': 500000,
                'gasPrice': w3.eth.gas_price
            })
            
            # Sign and send
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"✓ Transaction sent: {tx_hash.hex()}")
            print(f"  Waiting for confirmation...")
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"✅ NFT minted successfully!")
                # Extract token ID from logs
                token_id = receipt['logs'][0]['topics'][1].hex() if receipt['logs'] else "unknown"
                
                print(f"\n[3/3] Invoice tokenized!")
                print(f"✓ Token ID: #{token_id}")
                print(f"✓ View on BSCScan: https://testnet.bscscan.com/tx/{tx_hash.hex()}")
                
                return {
                    "success": True,
                    "token_id": token_id,
                    "tx_hash": tx_hash.hex(),
                    "face_value": amount_dollars,
                    "recommended_price": pricing['recommended_price'],
                    "discount": pricing['discount_percentage'],
                    "mode": "LIVE"
                }
            else:
                print("❌ Transaction failed")
                return None
                
        except Exception as e:
            print(f"❌ Blockchain error: {e}")
            return None
    
    def analyze_marketplace_opportunity(self, invoice_data, fraud_score):
        """
        Analyze if invoice is good candidate for tokenization
        """
        total_amount = invoice_data.get('total_amount', '0')
        
        # Handle both string and numeric types
        if isinstance(total_amount, (int, float)):
            amount = float(total_amount)
        else:
            # String type - clean it
            amount_str = str(total_amount).replace('$', '').replace(',', '').strip()
            try:
                amount = float(amount_str)
            except:
                amount = 0
        
        prompt = f"""
        Should this invoice be tokenized for early payment marketplace?
        
        Invoice:
        - Amount: ${amount}
        - Supplier: {invoice_data.get('supplier_name')}
        - Fraud Score: {fraud_score}/100
        
        Consider:
        - Is amount large enough? (min $500 recommended)
        - Is fraud risk acceptable? (max 30/100 recommended)
        - Would buyers be interested?
        
        Return JSON:
        {{
            "should_tokenize": <true/false>,
            "confidence": <0-100>,
            "reasons": ["reason1", "reason2"],
            "estimated_time_to_sell": "<hours/days>"
        }}
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
            
            return json.loads(result.strip())
        except:
            # Fallback
            return {
                "should_tokenize": amount >= 500 and fraud_score <= 30,
                "confidence": 70,
                "reasons": [f"Amount: ${amount}", f"Risk: {fraud_score}/100"],
                "estimated_time_to_sell": "1-3 days"
            }

if __name__ == "__main__":
    # Test the agent
    agent = InvoiceTokenizationAgent(mock_mode=True)
    
    # Sample invoice data
    test_invoice = {
        "supplier_name": "Acme Corp",
        "invoice_number": "INV-2024-001",
        "total_amount": "$1,500.00",
        "date": "2024-03-15"
    }
    
    test_hash = "a" * 64
    test_fraud_score = 15
    
    # Analyze
    analysis = agent.analyze_marketplace_opportunity(test_invoice, test_fraud_score)
    print("\nMarketplace Analysis:")
    print(json.dumps(analysis, indent=2))
    
    if analysis['should_tokenize']:
        # Tokenize
        result = agent.tokenize_invoice(test_hash, test_invoice, test_fraud_score)
        if result:
            print(f"\n✅ Success! Token #{result['token_id']} created")
