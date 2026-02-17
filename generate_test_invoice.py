"""
Quick script to create a simple test invoice with unique content
This ensures a different hash for testing
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import random

def create_test_invoice():
    filename = f"test_invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Create PDF
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Add content
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, height - 100, "TEST INVOICE")
    
    c.setFont("Helvetica", 12)
    y = height - 150
    
    # Unique identifier using timestamp and random number
    unique_id = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    
    content = [
        f"Invoice Number: {unique_id}",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "Supplier: Test Company Inc",
        "Customer: Demo Customer Ltd",
        "",
        "Items:",
        f"  - Test Service ${random.randint(100, 500)}.00",
        f"  - Test Product ${random.randint(50, 200)}.00",
        "",
        f"Total: ${random.randint(150, 700)}.00 USD",
        "",
        f"Generated: {datetime.now().isoformat()}",
    ]
    
    for line in content:
        c.drawString(100, y, line)
        y -= 20
    
    c.save()
    print(f"✅ Created: {filename}")
    print(f"   This file has a unique hash and can be registered on blockchain")
    return filename

if __name__ == "__main__":
    filename = create_test_invoice()
    print(f"\n💡 Now run: python agent.py {filename} --live")
