"""
Multi-Agent Invoice Processing Orchestrator with NFT Tokenization
Coordinates: Verification → Fraud Detection → Tokenization → Reconciliation
"""
import sys
from agent import InvoiceAgent
from agent_tokenization import InvoiceTokenizationAgent

class InvoiceOrchestrator:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        print("\n" + "="*70)
        print("  MULTI-AGENT INVOICE PROCESSING SYSTEM WITH NFT TOKENIZATION")
        print("="*70)
        print(f"Mode: {'MOCK (simulated blockchain)' if mock_mode else 'LIVE (real blockchain)'}\n")
        
        # Initialize agents
        print("Initializing agents...")
        self.verification_agent = InvoiceAgent(mock_mode=mock_mode)
        self.tokenization_agent = InvoiceTokenizationAgent(mock_mode=mock_mode)
        print("✓ All agents ready\n")
    
    def process_invoice_full_flow(self, invoice_path, enable_tokenization=True):
        """
        Complete invoice processing workflow:
        1. Verification & Registration
        2. Fraud Detection
        3. Tokenization (optional)
        4. Marketplace Listing
        """
        print("="*70)
        print(f"PROCESSING: {invoice_path}")
        print("="*70)
        
        # STEP 1: Verification & Blockchain Registration
        print("\n🔍 STEP 1: VERIFICATION & REGISTRATION")
        print("-" * 70)
        result = self.verification_agent.process_invoice(invoice_path)
        
        if not result:
            print("\n❌ Verification failed. Stopping workflow.")
            return None
        
        invoice_hash = result['document_hash']
        invoice_data = result['analysis']
        
        # STEP 2: Fraud Detection (from potential_issues)
        print("\n🚨 STEP 2: FRAUD DETECTION")
        print("-" * 70)
        
        issues = invoice_data.get('potential_issues', [])
        fraud_score = len(issues) * 10  # Simple scoring: 10 points per issue
        fraud_score = min(fraud_score, 100)
        
        print(f"Risk Score: {fraud_score}/100")
        if fraud_score > 50:
            print("⚠️  HIGH RISK - Manual review recommended")
        elif fraud_score > 30:
            print("⚠️  MEDIUM RISK - Proceed with caution")
        else:
            print("✓ LOW RISK - Safe to proceed")
        
        print(f"Issues detected: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        
        # STEP 3: Tokenization Decision
        if enable_tokenization:
            print("\n💎 STEP 3: NFT TOKENIZATION ANALYSIS")
            print("-" * 70)
            
            analysis = self.tokenization_agent.analyze_marketplace_opportunity(
                invoice_data,
                fraud_score
            )
            
            print(f"Should tokenize: {'YES' if analysis['should_tokenize'] else 'NO'}")
            print(f"Confidence: {analysis['confidence']}%")
            print(f"Reasons:")
            for reason in analysis.get('reasons', []):
                print(f"  - {reason}")
            
            if analysis['should_tokenize']:
                print(f"\n💰 STEP 4: TOKENIZING & LISTING")
                print("-" * 70)
                
                token_result = self.tokenization_agent.tokenize_invoice(
                    invoice_hash,
                    invoice_data,
                    fraud_score
                )
                
                if token_result and token_result['success']:
                    result['tokenization'] = token_result
                    result['marketplace_ready'] = True
                    
                    print("\n" + "="*70)
                    print("✅ INVOICE SUCCESSFULLY TOKENIZED!")
                    print("="*70)
                    print(f"\n📊 SUMMARY:")
                    print(f"  Original Invoice: {result['invoice_file']}")
                    print(f"  Document Hash: {invoice_hash[:16]}...{invoice_hash[-16:]}")
                    print(f"  Blockchain TX: {result['transaction_hash']}")
                    print(f"  NFT Token ID: #{token_result['token_id']}")
                    print(f"  Face Value: ${token_result['face_value']}")
                    print(f"  Listed Price: ${token_result['listed_price']}")
                    print(f"  Discount: {token_result['discount']}%")
                    print(f"  Risk Score: {fraud_score}/100")
                    print(f"\n💡 Buyers can purchase this invoice at a discount")
                    print(f"   and collect the full amount when the invoice is paid!")
                    
                else:
                    print("\n⚠️  Tokenization failed, but verification succeeded")
            else:
                print(f"\n⏭️  Skipping tokenization (not recommended for this invoice)")
                result['marketplace_ready'] = False
        
        return result
    
    def demo_marketplace(self):
        """
        Demo of marketplace functionality
        """
        print("\n" + "="*70)
        print("  INVOICE NFT MARKETPLACE DEMO")
        print("="*70)
        print("""
        🏪 MARKETPLACE FEATURES:
        
        1. TOKENIZATION
           - Convert verified invoices into tradeable NFTs
           - Each NFT represents claim to invoice payment
        
        2. AI PRICING
           - Analyze risk, time to maturity, supplier history
           - Calculate optimal discount for early payment
           - Market-competitive rates
        
        3. TRADING
           - Suppliers get immediate cash (at discount)
           - Buyers get profitable investment
           - Smart contract handles settlement
        
        4. REDEMPTION
           - When invoice paid → NFT holder gets full amount
           - Automatic profit calculation
           - Blockchain-verified settlement
        
        📈 EXAMPLE TRADE:
           Invoice Face Value: $10,000
           AI Recommended Price: $9,500 (5% discount)
           
           Supplier: Gets $9,500 immediately
           Buyer: Pays $9,500, gets $10,000 → $500 profit
           
        🔐 SECURITY:
           - Fraud detection filters risky invoices
           - Smart contract escrow
           - Immutable blockchain records
        """)

if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) < 2:
        print("\n📚 USAGE:")
        print("  python orchestrator_updated.py <invoice.pdf> [--live] [--no-tokenize]")
        print("\nEXAMPLES:")
        print("  python orchestrator_updated.py sample_invoice.pdf")
        print("  python orchestrator_updated.py sample_invoice.pdf --live")
        print("  python orchestrator_updated.py sample_invoice.pdf --live --no-tokenize")
        print("\nFLAGS:")
        print("  --live          Use real blockchain (requires tBNB)")
        print("  --no-tokenize   Skip NFT tokenization step")
        print("  --demo          Show marketplace demo")
        
        # Show demo by default
        orchestrator = InvoiceOrchestrator(mock_mode=True)
        orchestrator.demo_marketplace()
        sys.exit(0)
    
    # Parse arguments
    invoice_path = sys.argv[1]
    mock_mode = "--live" not in sys.argv
    enable_tokenization = "--no-tokenize" not in sys.argv
    
    if "--demo" in sys.argv:
        orchestrator = InvoiceOrchestrator(mock_mode=True)
        orchestrator.demo_marketplace()
        sys.exit(0)
    
    # Run full workflow
    orchestrator = InvoiceOrchestrator(mock_mode=mock_mode)
    result = orchestrator.process_invoice_full_flow(invoice_path, enable_tokenization)
    
    if result:
        # Save enhanced results
        import json
        from datetime import datetime
        
        output_file = f"tokenization_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n📄 Full results saved to: {output_file}")
