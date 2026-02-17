import os
import json
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
import time

load_dotenv()

# Web3 setup
w3 = Web3(Web3.HTTPProvider(os.getenv('BSC_TESTNET_RPC')))

class PaymentReconciliationAgent:
    def __init__(self, contract_address, mock_mode=True):
        self.contract_address = contract_address
        self.mock_mode = mock_mode
        self.pending_invoices = []
        print("Payment Reconciliation Agent initialized")
        print(f"Mode: {'MOCK' if mock_mode else 'LIVE'}")
        
    def load_pending_invoices(self, invoices_file="invoices_db.json"):
        """Load pending invoices from database"""
        try:
            with open(invoices_file, 'r') as f:
                data = json.load(f)
                self.pending_invoices = [inv for inv in data if inv.get('status') == 'pending']
            print(f"Loaded {len(self.pending_invoices)} pending invoices")
        except FileNotFoundError:
            print("No invoices database found. Starting fresh.")
            self.pending_invoices = []
    
    def monitor_wallet(self, wallet_address, start_block='latest'):
        """Monitor wallet for incoming transactions"""
        if self.mock_mode:
            # Mock incoming payment
            mock_payments = [
                {
                    'tx_hash': '0xmock123abc',
                    'from': '0x1234567890123456789012345678901234567890',
                    'to': wallet_address,
                    'value': 2380.00,  # matches sample invoice
                    'timestamp': datetime.now().isoformat(),
                    'block_number': 12345678
                }
            ]
            print(f"\nMonitoring wallet: {wallet_address[:10]}...")
            print(f"Found {len(mock_payments)} new transaction(s)")
            return mock_payments
        
        # Real blockchain monitoring
        try:
            latest_block = w3.eth.block_number
            print(f"\nMonitoring from block {latest_block}...")
            
            # Get recent transactions
            transactions = []
            for i in range(10):  # Check last 10 blocks
                block = w3.eth.get_block(latest_block - i, full_transactions=True)
                for tx in block.transactions:
                    if tx['to'] and tx['to'].lower() == wallet_address.lower():
                        transactions.append({
                            'tx_hash': tx['hash'].hex(),
                            'from': tx['from'],
                            'to': tx['to'],
                            'value': w3.from_wei(tx['value'], 'ether'),
                            'timestamp': datetime.fromtimestamp(block.timestamp).isoformat(),
                            'block_number': block.number
                        })
            
            print(f"Found {len(transactions)} transaction(s)")
            return transactions
            
        except Exception as e:
            print(f"Error monitoring blockchain: {e}")
            return []
    
    def match_payment_to_invoice(self, payment, tolerance=0.01):
        """Match a payment to a pending invoice"""
        payment_amount = float(payment['value'])
        
        for invoice in self.pending_invoices:
            invoice_total = float(invoice.get('total_amount', 0))
            
            # Match by amount (with small tolerance for rounding)
            if abs(payment_amount - invoice_total) <= tolerance:
                return {
                    'matched': True,
                    'invoice': invoice,
                    'payment': payment,
                    'match_type': 'exact',
                    'difference': 0
                }
            
            # Partial payment
            elif payment_amount < invoice_total and payment_amount > 0:
                return {
                    'matched': True,
                    'invoice': invoice,
                    'payment': payment,
                    'match_type': 'partial',
                    'difference': invoice_total - payment_amount,
                    'paid_percentage': (payment_amount / invoice_total) * 100
                }
        
        # No match found
        return {
            'matched': False,
            'payment': payment,
            'reason': 'No matching invoice found'
        }
    
    def reconcile_payments(self, wallet_address):
        """Main reconciliation function"""
        print(f"\n{'='*60}")
        print("Payment Reconciliation Process")
        print(f"{'='*60}")
        
        # Step 1: Load pending invoices
        print("\n[1/3] Loading pending invoices...")
        self.load_pending_invoices()
        
        if not self.pending_invoices:
            print("No pending invoices to reconcile")
            return []
        
        # Step 2: Monitor for payments
        print("\n[2/3] Monitoring blockchain for payments...")
        payments = self.monitor_wallet(wallet_address)
        
        if not payments:
            print("No new payments found")
            return []
        
        # Step 3: Match payments to invoices
        print("\n[3/3] Matching payments to invoices...")
        matches = []
        
        for payment in payments:
            match = self.match_payment_to_invoice(payment)
            matches.append(match)
            
            if match['matched']:
                if match['match_type'] == 'exact':
                    print("\nEXACT MATCH")
                    print(f"   Invoice: {match['invoice'].get('invoice_number')}")
                    print(f"   Amount: {payment['value']} {match['invoice'].get('currency', '')}")
                    print(f"   TX: {payment['tx_hash']}")
                    print("   Status: PAID")
                    
                elif match['match_type'] == 'partial':
                    print("\nPARTIAL PAYMENT")
                    print(f"   Invoice: {match['invoice'].get('invoice_number')}")
                    print(f"   Paid: {payment['value']} ({match['paid_percentage']:.1f}%)")
                    print(f"   Remaining: {match['difference']}")
                    print(f"   TX: {payment['tx_hash']}")
            else:
                print("\nUNMATCHED PAYMENT")
                print(f"   Amount: {payment['value']}")
                print(f"   TX: {payment['tx_hash']}")
                print(f"   Reason: {match['reason']}")
        
        # Save reconciliation report
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_payments': len(payments),
            'matched_payments': len([m for m in matches if m['matched']]),
            'unmatched_payments': len([m for m in matches if not m['matched']]),
            'matches': matches
        }
        
        report_file = f"reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("Reconciliation Complete")
        print(f"{'='*60}")
        print("Summary:")
        print(f"   Total payments: {report['total_payments']}")
        print(f"   Matched: {report['matched_payments']}")
        print(f"   Unmatched: {report['unmatched_payments']}")
        print(f"\nFull report saved to: {report_file}")
        
        return matches

if __name__ == "__main__":
    import sys
    
    agent = PaymentReconciliationAgent(
        contract_address=os.getenv('CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000'),
        mock_mode=True
    )
    
    if len(sys.argv) < 2:
        print("\nUsage: python agent_reconciliation.py <wallet_address>")
        print("   Example: python agent_reconciliation.py 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        sys.exit(1)
    
    wallet = sys.argv[1]
    agent.reconcile_payments(wallet)