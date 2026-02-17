README.md
# AI Invoice Verification Agent

**Good Vibes Only: OpenClaw Edition Submission**

An AI-powered agent that automatically verifies invoices and registers them on BNB Chain for fraud prevention and audit trail.

## 🎯 Problem Solved

- **Invoice Fraud Prevention**: Detect duplicates, anomalies, and suspicious amounts automatically
- **Immutable Audit Trail**: Every invoice gets a blockchain timestamp that can't be altered
- **AI-Powered Extraction**: Automatically parse invoices regardless of format
- **Cost Effective**: ~$0.01 per invoice verification on BSC

## 🤖 How It Works

1. Upload invoice (PDF)
2. AI (Google Gemini) extracts: supplier, amount, date, VAT, line items
3. Agent detects issues: duplicates, calculation errors, missing data
4. Document hash registered on BSC blockchain
5. Returns: BSCScan link + structured data

## 🛠️ Tech Stack

- **AI**: Google Gemini 1.5 Flash (invoice parsing & analysis)
- **Blockchain**: BNB Smart Chain Testnet
- **Language**: Python 3.13
- **Libraries**: web3.py, google-generativeai, PyPDF2

## 📦 Installation
```bash
# Clone repository
git clone <your-repo-url>
cd invoice-agent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## ⚙️ Configuration

Create `.env` file:
```
GOOGLE_API_KEY=your_google_api_key
WALLET_PRIVATE_KEY=your_metamask_private_key
BSC_TESTNET_RPC=https://data-seed-prebsc-1-s1.binance.org:8545/
CONTRACT_ADDRESS=<deployed_contract_address>
```

## 🚀 Usage

**Mock Mode (no blockchain needed):**
```bash
python agent.py sample_invoice.pdf
```

**Live Mode (real blockchain transactions):**
```bash
python agent.py sample_invoice.pdf --live
```

## 📊 Output Example
```
🔍 Processing Invoice: sample_invoice.pdf
[1/4] Extracting text from invoice...
✅ Extracted 1247 characters

[2/4] Analyzing with AI...
✅ Analysis complete:
   Supplier: Acme Corp
   Invoice #: INV-2024-001
   Date: 2024-01-15
   Total: 1500.00 EUR

⚠️  Potential Issues:
   - VAT calculation seems off (expected 285.00, found 280.00)

[3/4] Calculating document hash...
✅ Hash: a3f5d8e9c2b1a4f6...

[4/4] Registering on blockchain...
📝 Transaction Hash: 0x7a3c9e2f5b8d1a4c...
   Explorer: https://testnet.bscscan.com/tx/0x7a3c9e2f5b8d1a4c...

✨ SUCCESS! Invoice verified and registered
```

## 🎬 Demo

- **Video Demo**: [link to Loom/YouTube]
- **Live Contract**: https://testnet.bscscan.com/address/<contract_address>
- **Sample Transaction**: https://testnet.bscscan.com/tx/<tx_hash>

## 📋 Hackathon Requirements

✅ Onchain proof: Contract deployed on BSC Testnet  
✅ Reproducible: Public repo + setup instructions  
✅ AI-powered: Uses Google Gemini for invoice analysis  
✅ Demo link: Video demonstration included  
✅ Track: **Consumer** (business tools for non-technical users)

## 🔮 Future Use Case: conta.rocks Integration

This agent will be integrated into conta.rocks (accounting platform) to:
- Automatically verify client invoices on upload
- Prevent duplicate submissions
- Flag suspicious transactions for review
- Provide blockchain proof of invoice authenticity
- Enable instant audit trail for accountants

## 📄 License

MIT