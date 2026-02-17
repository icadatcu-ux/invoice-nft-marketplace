import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Import our agents
from agent import InvoiceAgent
from agent_fraud_detection import FraudDetectionAgent
from agent_reconciliation import PaymentReconciliationAgent

load_dotenv()

class InvoiceProcessingOrchestrator:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        
        # Initialize all agents
        self.invoice_agent = InvoiceAgent(mock_mode=mock_mode)
        self.fraud_agent = FraudDetectionAgent()
        self.reconciliation_agent = PaymentReconciliationAgent(
            contract_address=os.getenv('CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000'),
            mock_mode=mock_mode
        )
        
        print(f"\n{'='*70}")
        print("AI Invoice Processing System - Multi-Agent Orchestrator")
        print(f"{'='*70}")
        print(f"Mode: {'MOCK (Development)' if mock_mode else 'LIVE (Production)'}")
        print("\nActive Agents:")
        print("  1. Invoice Verification Agent")
        print("  2. Fraud Detection & Risk Scoring Agent")
        print("  3. Payment Reconciliation Agent")
        print(f"{'='*70}\n")
    
    def process_invoice_full_workflow(self, invoice_path):
        """Complete end-to-end invoice processing workflow"""
        
        print("\nStarting Full Invoice Processing Workflow")
        print(f"File: {os.path.basename(invoice_path)}\n")
        
        # ============================================================
        # STAGE 1: Invoice Verification & Onchain Registration
        # ============================================================
        print(f"\n{'='*70}")
        print(f"STAGE 1: Invoice Verification & Blockchain Registration")
        print(f"{'='*70}")
        
        result = self.invoice_agent.process_invoice(invoice_path)
        
        if not result:
            print("\nInvoice verification failed. Workflow terminated.")
            return None
        
        # Save to database
        self.save_to_database(result)
        
        # ============================================================
        # STAGE 2: Fraud Detection & Risk Analysis
        # ============================================================
        print(f"\n{'='*70}")
        print(f"STAGE 2: Fraud Detection & Risk Analysis")
        print(f"{'='*70}")
        
        fraud_report = self.fraud_agent.analyze_invoice(result)
        
        # Add fraud analysis to result
        result['fraud_analysis'] = fraud_report
        
        # Check if invoice should be blocked
        if fraud_report.get('ai_analysis', {}).get('recommended_action') == 'reject':
            print("\nINVOICE REJECTED due to high fraud risk")
            print(f"   Reason: {fraud_report.get('ai_analysis', {}).get('explanation')}")
            result['status'] = 'rejected'
            self.update_database(result)
            return result
        
        elif len(fraud_report.get('detected_issues', [])) > 0:
            print("\nINVOICE FLAGGED FOR REVIEW")
            result['status'] = 'pending_review'
        else:
            print("\nINVOICE APPROVED - No fraud indicators")
            result['status'] = 'approved'
        
        self.update_database(result)
        
        # ============================================================
        # STAGE 3: Payment Monitoring (Optional)
        # ============================================================
        print(f"\n{'='*70}")
        print(f"STAGE 3: Payment Reconciliation (Future Monitoring)")
        print(f"{'='*70}")
        
        print("\nInvoice registered for payment monitoring")
        print(f"   When payment arrives onchain, Agent 2 will automatically:")
        print(f"   • Detect the incoming transaction")
        print(f"   • Match it to this invoice")
        print(f"   • Update status to 'paid'")
        print(f"   • Close the invoice")
        
        # ============================================================
        # Final Report
        # ============================================================
        print(f"\n{'='*70}")
        print("WORKFLOW COMPLETE")
        print(f"{'='*70}")
        
        print("\nFinal Status Summary:")
        print(f"   Invoice Number: {result.get('analysis', {}).get('invoice_number', 'N/A')}")
        print(f"   Supplier: {result.get('analysis', {}).get('supplier_name', 'N/A')}")
        print(f"   Amount: {result.get('analysis', {}).get('total_amount', 'N/A')} {result.get('analysis', {}).get('currency', '')}")
        print(f"   Status: {result.get('status', 'unknown').upper()}")
        print(f"   Fraud Issues: {len(fraud_report.get('detected_issues', []))} detected")
        print(f"   Risk Level: {fraud_report.get('supplier_risk', {}).get('level', 'unknown').upper()}")
        print(f"   Blockchain TX: {result.get('transaction_hash', 'N/A')}")
        
        # Save complete workflow report
        workflow_report = {
            'timestamp': datetime.now().isoformat(),
            'invoice_verification': result,
            'fraud_analysis': fraud_report,
            'final_status': result.get('status'),
            'workflow_complete': True
        }
        
        report_file = f"workflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(workflow_report, f, indent=2)
        
        print(f"\nComplete workflow report: {report_file}")
        
        return workflow_report
    
    def save_to_database(self, invoice_result):
        """Save invoice to persistent database"""
        db_file = "invoices_db.json"
        
        try:
            with open(db_file, 'r') as f:
                db = json.load(f)
        except FileNotFoundError:
            db = []
        
        # Add new invoice
        invoice_record = {
            'invoice_number': invoice_result.get('analysis', {}).get('invoice_number'),
            'supplier_name': invoice_result.get('analysis', {}).get('supplier_name'),
            'total_amount': invoice_result.get('analysis', {}).get('total_amount'),
            'currency': invoice_result.get('analysis', {}).get('currency'),
            'date': invoice_result.get('analysis', {}).get('date'),
            'document_hash': invoice_result.get('document_hash'),
            'transaction_hash': invoice_result.get('transaction_hash'),
            'timestamp': invoice_result.get('timestamp'),
            'status': invoice_result.get('status', 'pending'),
            'flags': []
        }
        
        db.append(invoice_record)
        
        with open(db_file, 'w') as f:
            json.dump(db, f, indent=2)
        
        print("\nInvoice saved to database")
    
    def update_database(self, invoice_result):
        """Update existing invoice in database"""
        db_file = "invoices_db.json"
        
        try:
            with open(db_file, 'r') as f:
                db = json.load(f)
            
            # Find and update
            invoice_num = invoice_result.get('analysis', {}).get('invoice_number')
            for record in db:
                if record['invoice_number'] == invoice_num:
                    record['status'] = invoice_result.get('status')
                    if invoice_result.get('fraud_analysis'):
                        record['flags'] = [
                            issue.get('reason', 'Unknown issue') 
                            for issue in invoice_result['fraud_analysis'].get('detected_issues', [])
                        ]
                    break
            
            with open(db_file, 'w') as f:
                json.dump(db, f, indent=2)
                
        except FileNotFoundError:
            pass
    
    def run_payment_reconciliation(self, wallet_address):
        """Run payment reconciliation for all pending invoices"""
        print(f"\n{'='*70}")
        print("Running Payment Reconciliation")
        print(f"{'='*70}")
        
        matches = self.reconciliation_agent.reconcile_payments(wallet_address)
        return matches

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("   Process invoice:  python orchestrator.py <invoice.pdf>")
        print("   Reconcile payments: python orchestrator.py --reconcile <wallet_address>")
        print("\n   Add --live flag for real blockchain transactions")
        sys.exit(1)
    
    # Check for live mode
    live_mode = "--live" in sys.argv
    if live_mode:
        sys.argv.remove("--live")
    
    orchestrator = InvoiceProcessingOrchestrator(mock_mode=not live_mode)
    
    # Payment reconciliation mode
    if sys.argv[1] == "--reconcile":
        if len(sys.argv) < 3:
            print("Error: Wallet address required for reconciliation")
            sys.exit(1)
        
        wallet = sys.argv[2]
        orchestrator.run_payment_reconciliation(wallet)
    
    # Invoice processing mode
    else:
        invoice_path = sys.argv[1]
        # Resolve sample_invoice.pdf -> sample_invoice.pdf.pdf if needed
        if not os.path.exists(invoice_path):
            for cand in [f"{invoice_path}.pdf", invoice_path + ".pdf"]:
                if cand != invoice_path and os.path.exists(cand):
                    invoice_path = cand
                    break
        if not os.path.exists(invoice_path):
            print(f"Error: File not found: {invoice_path}")
            sys.exit(1)
        orchestrator.process_invoice_full_workflow(invoice_path)