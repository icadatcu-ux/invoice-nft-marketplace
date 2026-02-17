import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import google.generativeai as genai
import statistics

load_dotenv()

# Configure AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

def _safe_float(val, default=0.0):
    """Convert to float; return default for placeholders/invalid values."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace(" ", "")
    # Strip leading currency/symbols, keep digits and one decimal
    import re
    m = re.search(r"[-]?\d+\.?\d*", s)
    if not m:
        return default
    try:
        return float(m.group(0))
    except ValueError:
        return default


class FraudDetectionAgent:
    def __init__(self):
        self.invoices_db = []
        self.risk_scores = {}
        self.fraud_patterns = []
        print("Fraud Detection & Risk Scoring Agent initialized")
        
    def load_invoices_database(self, db_file="invoices_db.json"):
        """Load all processed invoices"""
        try:
            with open(db_file, 'r') as f:
                self.invoices_db = json.load(f)
            print(f"Loaded {len(self.invoices_db)} invoices from database")
        except FileNotFoundError:
            print("No invoice database found. Will analyze uploaded invoices only.")
            self.invoices_db = []
    
    def detect_duplicate_invoices(self, invoice):
        """Detect potential duplicate invoices"""
        duplicates = []
        
        supplier = invoice.get('supplier_name', '').lower()
        amount = _safe_float(invoice.get('total_amount'))
        invoice_num = invoice.get('invoice_number', '')
        
        for existing in self.invoices_db:
            # Exact duplicate by invoice number
            if existing.get('invoice_number') == invoice_num:
                duplicates.append({
                    'type': 'exact_duplicate',
                    'severity': 'critical',
                    'match': existing,
                    'reason': f"Duplicate invoice number: {invoice_num}"
                })
            
            # Same supplier + same amount within 30 days
            if existing.get('supplier_name', '').lower() == supplier:
                existing_amount = _safe_float(existing.get('total_amount'))
                if abs(amount - existing_amount) < 0.01:
                    # Check date proximity
                    try:
                        existing_date = datetime.fromisoformat(existing.get('timestamp', datetime.now().isoformat()))
                        current_date = datetime.now()
                        
                        if abs((current_date - existing_date).days) <= 30:
                            duplicates.append({
                                'type': 'suspicious_duplicate',
                                'severity': 'high',
                                'match': existing,
                                'reason': f"Same supplier + amount within 30 days"
                            })
                    except:
                        pass
        
        return duplicates
    
    def detect_round_number_fraud(self, invoice):
        """Detect suspicious round numbers (potential fraud indicator)"""
        amount = _safe_float(invoice.get('total_amount'))
        
        # Check if it's a very round number
        if amount > 1000 and amount % 1000 == 0:
            return {
                'detected': True,
                'severity': 'medium',
                'reason': f"Suspiciously round amount: {amount} (possible fabricated invoice)"
            }
        
        if amount > 100 and amount % 100 == 0 and amount < 1000:
            return {
                'detected': True,
                'severity': 'low',
                'reason': f"Round number: {amount} (common but worth reviewing)"
            }
        
        return {'detected': False}
    
    def detect_velocity_attack(self, invoice):
        """Detect too many invoices from same supplier in short time"""
        supplier = invoice.get('supplier_name', '').lower()
        
        # Count invoices from this supplier in last 7 days
        recent_count = 0
        for existing in self.invoices_db:
            if existing.get('supplier_name', '').lower() == supplier:
                try:
                    existing_date = datetime.fromisoformat(existing.get('timestamp', datetime.now().isoformat()))
                    if (datetime.now() - existing_date).days <= 7:
                        recent_count += 1
                except:
                    pass
        
        if recent_count >= 5:
            return {
                'detected': True,
                'severity': 'high',
                'count': recent_count,
                'reason': f"{recent_count} invoices from {supplier} in 7 days (velocity attack pattern)"
            }
        
        return {'detected': False}
    
    def detect_calculation_anomalies(self, invoice):
        """Use AI to verify calculations (VAT, totals, etc.)"""
        line_items = invoice.get('line_items', [])
        total = _safe_float(invoice.get('total_amount'))
        vat = _safe_float(invoice.get('vat_amount'))
        
        if not line_items:
            return {'detected': False}
        
        # Calculate expected total from line items
        calculated_subtotal = sum([
            _safe_float(item.get('total')) for item in line_items
        ])
        
        # Check if total matches
        expected_total = calculated_subtotal + vat
        
        if abs(total - expected_total) > 1.0:  # Tolerance of 1 unit
            return {
                'detected': True,
                'severity': 'high',
                'reason': f"Total mismatch: Expected {expected_total}, got {total}",
                'discrepancy': total - expected_total
            }
        
        return {'detected': False}
    
    def calculate_risk_score(self, supplier_name):
        """Calculate risk score for a supplier based on historical data"""
        supplier = supplier_name.lower()
        supplier_invoices = [
            inv for inv in self.invoices_db 
            if inv.get('supplier_name', '').lower() == supplier
        ]
        
        if not supplier_invoices:
            return {
                'score': 50,  # Neutral for new suppliers
                'level': 'medium',
                'reason': 'New supplier - no historical data'
            }
        
        risk_factors = 0
        total_factors = 0
        
        # Factor 1: Number of flagged invoices
        flagged = len([inv for inv in supplier_invoices if inv.get('flags', [])])
        total_factors += 1
        if flagged > len(supplier_invoices) * 0.3:  # More than 30% flagged
            risk_factors += 1
        
        # Factor 2: Amount variance (high variance = risky)
        amounts = [_safe_float(inv.get('total_amount')) for inv in supplier_invoices]
        if len(amounts) > 1:
            total_factors += 1
            avg = statistics.mean(amounts)
            std = statistics.stdev(amounts)
            if std > avg * 0.5:  # High variance
                risk_factors += 1
        
        # Factor 3: Invoice frequency (too frequent = suspicious)
        total_factors += 1
        if len(supplier_invoices) > 10:  # More than 10 invoices
            dates = []
            for inv in supplier_invoices:
                try:
                    dates.append(datetime.fromisoformat(inv.get('timestamp')))
                except:
                    pass
            
            if dates:
                dates.sort()
                avg_days_between = sum([
                    (dates[i+1] - dates[i]).days 
                    for i in range(len(dates)-1)
                ]) / (len(dates) - 1)
                
                if avg_days_between < 3:  # Less than 3 days average
                    risk_factors += 1
        
        # Calculate score (0-100, lower is better)
        risk_score = (risk_factors / total_factors) * 100 if total_factors > 0 else 50
        
        if risk_score < 30:
            level = 'low'
        elif risk_score < 60:
            level = 'medium'
        else:
            level = 'high'
        
        return {
            'score': round(risk_score),
            'level': level,
            'total_invoices': len(supplier_invoices),
            'flagged_invoices': flagged
        }
    
    def analyze_with_ai(self, invoice, detected_issues):
        """Use AI to provide additional fraud analysis"""
        prompt = f"""
        Analyze this invoice for potential fraud indicators.
        
        Invoice data:
        {json.dumps(invoice, indent=2)}
        
        Already detected issues:
        {json.dumps(detected_issues, indent=2)}
        
        Provide:
        1. Additional fraud indicators not covered by rules
        2. Overall fraud probability (low/medium/high)
        3. Recommended action (approve/review/reject)
        4. Brief explanation
        
        Return as JSON with keys: additional_indicators (array), fraud_probability, recommended_action, explanation
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
            
            return json.loads(result)
        except Exception as e:
            return {
                'additional_indicators': [],
                'fraud_probability': 'unknown',
                'recommended_action': 'review',
                'explanation': f'AI analysis failed: {str(e)}'
            }
    
    def analyze_invoice(self, invoice_data):
        """Main fraud detection analysis"""
        print(f"\n{'='*60}")
        print("Fraud Detection Analysis")
        print(f"{'='*60}")
        
        invoice = invoice_data.get('analysis', invoice_data)
        
        print(f"\nInvoice: {invoice.get('invoice_number', 'N/A')}")
        print(f"   Supplier: {invoice.get('supplier_name', 'N/A')}")
        print(f"   Amount: {invoice.get('total_amount', 'N/A')} {invoice.get('currency', '')}")
        
        # Load historical data
        print("\n[1/6] Loading historical invoice data...")
        self.load_invoices_database()
        
        detected_issues = []
        
        # Check 1: Duplicates
        print("\n[2/6] Checking for duplicate invoices...")
        duplicates = self.detect_duplicate_invoices(invoice)
        if duplicates:
            detected_issues.extend(duplicates)
            for dup in duplicates:
                print(f"   WARN {dup['severity'].upper()}: {dup['reason']}")
        else:
            print("   No duplicates detected")
        
        # Check 2: Round numbers
        print("\n[3/6] Analyzing amount patterns...")
        round_fraud = self.detect_round_number_fraud(invoice)
        if round_fraud['detected']:
            detected_issues.append(round_fraud)
            print(f"   WARN {round_fraud['severity'].upper()}: {round_fraud['reason']}")
        else:
            print("   Amount appears legitimate")
        
        # Check 3: Velocity attack
        print("\n[4/6] Checking invoice frequency...")
        velocity = self.detect_velocity_attack(invoice)
        if velocity['detected']:
            detected_issues.append(velocity)
            print(f"   WARN {velocity['severity'].upper()}: {velocity['reason']}")
        else:
            print("   Normal invoice frequency")
        
        # Check 4: Calculation errors
        print("\n[5/6] Verifying calculations...")
        calc_error = self.detect_calculation_anomalies(invoice)
        if calc_error['detected']:
            detected_issues.append(calc_error)
            print(f"   WARN {calc_error['severity'].upper()}: {calc_error['reason']}")
        else:
            print("   Calculations correct")
        
        # Calculate supplier risk score
        supplier_risk = self.calculate_risk_score(invoice.get('supplier_name', ''))
        print(f"\nSupplier Risk Score: {supplier_risk['score']}/100 ({supplier_risk['level']})")
        print(f"   Historical invoices: {supplier_risk.get('total_invoices', 0)}")
        
        # AI analysis
        print("\n[6/6] AI-powered fraud analysis...")
        ai_analysis = self.analyze_with_ai(invoice, detected_issues)
        
        # Final verdict
        print(f"\n{'='*60}")
        print("Analysis Summary")
        print(f"{'='*60}")
        print(f"Issues detected: {len(detected_issues)}")
        print(f"Fraud probability: {ai_analysis.get('fraud_probability', 'unknown').upper()}")
        print(f"Recommended action: {ai_analysis.get('recommended_action', 'review').upper()}")
        print(f"\nAI Insight: {ai_analysis.get('explanation', 'N/A')}")
        
        # Save analysis report
        report = {
            'timestamp': datetime.now().isoformat(),
            'invoice': invoice,
            'detected_issues': detected_issues,
            'supplier_risk': supplier_risk,
            'ai_analysis': ai_analysis,
            'total_issues': len(detected_issues)
        }
        
        report_file = f"fraud_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nFull report saved to: {report_file}")
        
        return report

if __name__ == "__main__":
    import sys
    
    agent = FraudDetectionAgent()
    
    if len(sys.argv) < 2:
        print("\nUsage: python agent_fraud_detection.py <result_file.json>")
        print("   Example: python agent_fraud_detection.py result_20240210_220724.json")
        print("\n   Analyzes an invoice result from the verification agent")
        sys.exit(1)
    
    result_file = sys.argv[1]
    
    if not os.path.exists(result_file):
        print(f"Error: File not found: {result_file}")
        sys.exit(1)
    
    # Load invoice data
    with open(result_file, 'r') as f:
        invoice_data = json.load(f)
    
    # Run fraud analysis
    agent.analyze_invoice(invoice_data)