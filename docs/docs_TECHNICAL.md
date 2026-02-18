# Technical Documentation

## System Architecture

### High-Level Overview

```
┌─────────────┐
│   Invoice   │
│   (PDF)     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│      Verification Agent                 │
│  • Gemini AI parsing                    │
│  • Document hash calculation            │
│  • Blockchain registration              │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│      Fraud Detection Agent              │
│  • Pattern analysis                     │
│  • Risk scoring (0-100)                 │
│  • Duplicate detection                  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│      Tokenization Agent                 │
│  • AI viability analysis                │
│  • Smart pricing calculation            │
│  • NFT minting (if approved)            │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│      Reconciliation Agent               │
│  • Payment monitoring                   │
│  • NFT redemption triggers              │
│  • Settlement verification              │
└─────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Python 3.13
- Web3.py (blockchain interaction)
- google-generativeai (Gemini AI SDK)
- PyPDF2 (PDF parsing)
- python-dotenv (configuration)

**Blockchain:**
- Solidity 0.8.0+
- BNB Chain (BSC Testnet)
- Contract deployment via Remix

**AI:**
- Gemini 2.0 Flash model
- Prompt engineering for structured extraction
- AI decision-making for pricing and approval

---

## Smart Contracts

### 1. Invoice Registry Contract

**Purpose:** Immutable record of verified invoices

**Key Functions:**
```solidity
registerInvoice(bytes32 _invoiceHash, string _metadata)
getInvoice(bytes32 _invoiceHash) → (timestamp, registrar, metadata)
verifyInvoice(bytes32 _invoiceHash) → bool
```

**Deployed:** `0xfde796D7E133A61636eD51f1e2F145C35b28617b`

**Design Decisions:**
- Stores only hash onchain (not full invoice data) for privacy
- Metadata as JSON string for flexibility
- Events for external monitoring
- No centralized admin (permissionless)

### 2. Invoice NFT Contract

**Purpose:** Tokenization and marketplace

**Key Functions:**
```solidity
mintInvoice(bytes32 hash, uint256 amount, uint256 dueDate, uint8 riskScore, string metadata)
listInvoice(uint256 tokenId, uint256 price)
buyInvoice(uint256 tokenId) payable
redeemInvoice(uint256 tokenId) payable
calculateRecommendedPrice(uint256 tokenId) → uint256
```

**Status:** Designed and tested in mock mode, ready for deployment

**Design Decisions:**
- ERC-721 compatible NFT
- Onchain risk score storage
- AI-powered pricing function
- Escrow-free design (direct transfers)

---

## Setup Instructions

### Prerequisites

- Python 3.8+
- MetaMask wallet with BSC Testnet configured
- tBNB for gas (get from: https://testnet.bnbchain.org/faucet-smart)
- Gemini AI API key (free: https://aistudio.google.com/app/apikey)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/invoice-nft-marketplace.git
cd invoice-nft-marketplace

# Install dependencies
pip install web3 python-dotenv google-generativeai PyPDF2 reportlab

# Or use requirements.txt
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials:
# WALLET_PRIVATE_KEY=<your_private_key_without_0x>
# GOOGLE_API_KEY=<your_gemini_api_key>
# CONTRACT_ADDRESS=0xfde796D7E133A61636eD51f1e2F145C35b28617b
# BSC_TESTNET_RPC=https://data-seed-prebsc-1-s1.binance.org:8545/
```

**⚠️ Security Note:** Never commit `.env` file. The `.gitignore` is configured to exclude it.

---

## Running the System

### Mock Mode (No Gas Required)

```bash
# Test with sample invoice
python orchestrator_updated.py sample_invoice.pdf

# Generate test invoice
python generate_test_invoice.py
python orchestrator_updated.py test_invoice_*.pdf
```

**Output:**
- Invoice verification results
- Risk analysis
- AI tokenization decision
- Mock transaction hash

### Live Mode (Requires tBNB)

```bash
# Process invoice with real blockchain transactions
python orchestrator_updated.py sample_invoice.pdf --live

# Generate and process new invoice
python generate_test_invoice.py
python orchestrator_updated.py test_invoice_*.pdf --live
```

**What Happens:**
1. AI extracts invoice data
2. Fraud detection scores risk
3. If risk acceptable: registers hash onchain
4. AI analyzes tokenization viability
5. If approved: returns pricing recommendation
6. Transaction confirmed on BSC Testnet

### Diagnostic Tools

```bash
# Test blockchain connection and contract
python test_contract.py
```

**Checks:**
- BSC RPC connection
- Wallet balance
- Contract deployment
- Gas estimation

---

## Demo Walkthrough

### Scenario: Processing a Real Invoice

**Step 1: Preparation**
```bash
cd invoice-nft-marketplace
python generate_test_invoice.py
# Creates: test_invoice_YYYYMMDD_HHMMSS.pdf
```

**Step 2: Run Orchestrator**
```bash
python orchestrator_updated.py test_invoice_20260218_101231.pdf --live
```

**Expected Output:**
```
[1/4] Extracting text from invoice...
✓ Extracted 439 characters

[2/4] Analyzing with AI...
✓ Analysis complete:
   Supplier: Test Company Inc
   Invoice #: INV-2024-001
   Total: $647.00 USD

[3/4] Fraud Detection...
Risk Score: 30/100
✓ LOW RISK - Safe to proceed

[4/4] NFT Tokenization Analysis...
Should tokenize: YES (if risk ≤30) or NO (if risk >30)

🔄 Signing transaction...
✅ REAL TRANSACTION SENT!
   Hash: 0x...
   Explorer: https://testnet.bscscan.com/tx/0x...
```

**Step 3: Verify on BSCScan**
- Open the transaction link
- Confirm status: Success ✓
- View contract interaction details

---

## Code Structure

```
invoice-nft-marketplace/
├── agent.py                      # Verification Agent
├── agent_fraud_detection.py      # Fraud Detection Agent  
├── agent_tokenization.py         # Tokenization Agent (NEW)
├── agent_reconciliation.py       # Reconciliation Agent
├── orchestrator_updated.py       # Multi-agent coordinator
├── contract.sol                  # Invoice Registry (deployed)
├── InvoiceNFT.sol               # NFT Marketplace contract
├── test_contract.py             # Diagnostic utility
├── generate_test_invoice.py     # Test data generator
├── requirements.txt             # Python dependencies
├── .env.example                 # Configuration template
├── .gitignore                   # Excludes secrets
├── bsc.address                  # Deployment info
├── README.md                    # Main documentation
└── docs/
    ├── PROJECT.md               # This file
    ├── TECHNICAL.md             # You are here
    └── EXTRAS.md                # Demo video links
```

---

## Testing

### Unit Testing

```bash
# Test individual agents
python -m pytest test/

# Test contract interactions
python test_contract.py
```

### Integration Testing

```bash
# Mock mode (no blockchain)
python orchestrator_updated.py sample_invoice.pdf

# Live mode (with blockchain)
python orchestrator_updated.py test_invoice.pdf --live
```

### Test Coverage

- ✅ PDF parsing with various formats
- ✅ AI extraction accuracy
- ✅ Fraud detection patterns
- ✅ Contract registration
- ✅ Gas estimation
- ✅ Error handling
- ✅ Multi-agent coordination

---

## Performance Metrics

**Processing Speed:**
- PDF extraction: ~1 second
- AI analysis: ~2-3 seconds
- Fraud detection: <1 second
- Blockchain transaction: ~3 seconds (BSC block time)
- **Total: ~7-10 seconds** per invoice

**Costs:**
- Gemini AI: Free tier (1500 requests/day)
- BSC Testnet: Free (tBNB from faucet)
- Mainnet estimate: ~$0.01 per invoice registration

**Scalability:**
- Current: Single-threaded Python
- Target: 1000+ invoices/day
- Future: Parallel processing, batch operations

---

## Troubleshooting

### "WALLET_PRIVATE_KEY not set"
- Check `.env` file exists in root directory
- Ensure private key has no `0x` prefix
- Verify no spaces or newlines

### "Insufficient funds"
- Check wallet balance: Should have >0.001 tBNB
- Get tBNB: https://testnet.bnbchain.org/faucet-smart
- Wait 10 min after faucet request

### "AI unavailable" or quota errors
- Gemini API free tier: 1500 requests/day
- Create new API key if needed
- System falls back to local parsing if AI fails

### "Transaction failed"
- Check BSCScan link for specific error
- Common: Invoice already registered (duplicate)
- Solution: Use different invoice file

### "Connection refused"
- BSC RPC may be temporarily down
- Try alternative: `https://bsc-testnet-rpc.publicnode.com`
- Update in `.env` file

---

## Security Considerations

**Implemented:**
- ✅ Private keys never hardcoded
- ✅ Environment variables for secrets
- ✅ `.gitignore` excludes sensitive files
- ✅ Input validation and sanitization
- ✅ Smart contract access controls
- ✅ Fraud detection before blockchain interaction

**Future Enhancements:**
- Hardware wallet integration
- Multi-signature for high-value invoices
- Rate limiting on API endpoints
- Encrypted invoice storage
- Formal smart contract audit

---

## API Integration (Future)

**Planned REST API:**

```bash
POST /api/v1/invoice/verify
POST /api/v1/invoice/tokenize
GET  /api/v1/invoice/{hash}
GET  /api/v1/marketplace/listings
POST /api/v1/marketplace/buy/{tokenId}
```

**Webhook Support:**
- Invoice verification complete
- Risk score calculated
- NFT minted
- Payment received
- NFT redeemed

---

## Contributing

This is a hackathon project, but contributions welcome post-event:

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

**Areas for contribution:**
- Additional fraud detection patterns
- UI/frontend development
- Multi-chain support
- Mobile app development
- ML risk modeling

---

## License

MIT License - See LICENSE file for details

---

## Support

**Hackathon:** Good Vibes Only: OpenClaw Edition  
**Track:** Agent (AI Agent × Onchain Actions)  
**Repo:** https://github.com/YOUR_USERNAME/invoice-nft-marketplace  
**Demo:** [Link in EXTRAS.md]
