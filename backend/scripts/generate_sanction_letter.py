import argparse
import sys
import os

# Add backend directory to path so we can import from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.repository import get_platform_repository
from services.case_service import CaseService
from models.platform_schema import CaseStatus

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Business Loan Sanction Letter</title>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            margin: 40px auto;
            max-width: 800px;
            color: #333;
            line-height: 1.5;
            padding: 20px;
            border: 1px solid #ccc;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0; color: #2c3e50; font-size: 24px; text-transform: uppercase; }}
        .header p {{ margin: 5px 0; font-size: 14px; font-weight: bold; }}
        .ref-date {{ display: flex; justify-content: space-between; margin-bottom: 30px; font-weight: bold; }}
        .recipient {{ margin-bottom: 30px; }}
        .recipient p {{ margin: 2px 0; }}
        .subject {{ font-weight: bold; text-decoration: underline; text-align: center; margin-bottom: 30px; }}
        .body-text {{ text-align: justify; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th, td {{ border: 1px solid #000; padding: 10px; text-align: left; }}
        th {{ background-color: #f2f2f2; width: 35%; }}
        .signatures {{ margin-top: 60px; display: flex; justify-content: space-between; }}
        .sig-block {{ width: 40%; border-top: 1px solid #000; padding-top: 5px; font-weight: bold; text-align: center; }}
        .footer {{ text-align: center; font-size: 11px; margin-top: 40px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Kira Capital Finance Ltd.</h1>
        <p>Registered Office: 1st Floor, Tech Park, Bangalore, KA, India - 560100</p>
        <p>Email: loans@kirafinance.com | Contact: 1800-123-4567</p>
    </div>

    <div class="ref-date">
        <span>Ref No: KCF/SL/{case_id_short}/2026</span>
        <span>Date: {date_str}</span>
    </div>

    <div class="recipient">
        <p><strong>To,</strong></p>
        <p><strong>{store_name}</strong></p>
        <p>Attn: {owner_name}</p>
        <p>Address: {district}, {state} - {pincode}</p>
        <p>Mobile: {mobile}</p>
    </div>

    <div class="subject">
        Subject: Sanction of Business Loan Facility
    </div>

    <div class="body-text">
        Dear Sir/Madam, <br><br>
        With reference to your loan application and subsequent discussions, we are pleased to inform you that Kira Capital Finance Ltd. has sanctioned a Business Loan in favor of <strong>{store_name}</strong>, subject to the terms and conditions outlined below.
    </div>

    <table>
        <tr>
            <th>Facility Type</th>
            <td>Unsecured Business Term Loan</td>
        </tr>
        <tr>
            <th>Sanctioned Amount</th>
            <td><strong>Rs. {amount}</strong> (Rupees {amount_words} Only)</td>
        </tr>
        <tr>
            <th>Purpose of Loan</th>
            <td>Working Capital & Inventory Purchase</td>
        </tr>
        <tr>
            <th>Tenure</th>
            <td>{tenure} Months</td>
        </tr>
        <tr>
            <th>Annual Interest Rate</th>
            <td>{rate}% per annum (Fixed)</td>
        </tr>
        <tr>
            <th>Estimated Installment (EMI)</th>
            <td>Rs. {emi} per month</td>
        </tr>
        <tr>
            <th>Processing Fee</th>
            <td>2.00% of the Sanctioned Amount + Applicable GST</td>
        </tr>
        <tr>
            <th>Prepayment Charges</th>
            <td>4.00% on principal outstanding if closed before 6 months.</td>
        </tr>
        <tr>
            <th>Security / Collateral</th>
            <td>Nil (Unsecured)</td>
        </tr>
    </table>

    <div class="body-text">
        <strong>Important Conditions:</strong>
        <ol>
            <li>The loan shall be disbursed only upon completion of KYC authentication, execution of the Loan Agreement, and successful mandate registration (NACH/e-Mandate) in favor of the Lender.</li>
            <li>This sanction is valid for 15 days from the date of this letter. If not accepted within this period, the offer will automatically lapse.</li>
            <li>The Lender reserves the right to cancel this sanction unconditionally or recall the facility if any material adverse changes in the business operations or credit profile are detected.</li>
        </ol>
    </div>

    <div class="body-text">
        Please sign and return the duplicate copy of this letter as a token of your unconditional acceptance of the terms and conditions mentioned herein.
    </div>

    <p style="margin-top: 40px;">Yours Faithfully,</p>
    <div style="margin-bottom: 60px;"><strong>For Kira Capital Finance Ltd.</strong><br><br><br><br>Authorized Signatory</div>

    <div class="signatures">
        <div class="sig-block">
            Accepted by Borrower<br>
            ({store_name})
        </div>
        <div class="sig-block">
            Guarantor (If any)
        </div>
    </div>

    <div class="footer">
        This is a system-generated document based on KIRA AI Platform logic. Kira Capital Finance Ltd. is a registered NBFC under the Reserve Bank of India.
    </div>
</body>
</html>
"""

def generate_sanction_letter(case_id_str: str):
    import datetime
    import uuid
    import math

    repo = get_platform_repository()
    case_service = CaseService(repo, None, None)
    
    try:
        case_id = uuid.UUID(case_id_str)
        detail = case_service.get_case_detail(case_id)
    except Exception as e:
        print(f"Error loading case: {{e}}")
        return

    kirana = detail.kirana
    assessment = detail.latest_assessment
    
    amount = 0
    emi = 0
    rate = 22.5
    tenure = 12
    if assessment and assessment.recommended_amount:
        amount = assessment.recommended_amount
    elif detail.case.latest_loan_range:
        amount = detail.case.latest_loan_range.high
        
    if assessment and assessment.estimated_emi:
        emi = assessment.estimated_emi

    if detail.underwriting_decision and detail.underwriting_decision.final_terms:
        amount = detail.underwriting_decision.final_terms.amount
        emi = detail.underwriting_decision.final_terms.estimated_installment
        tenure = detail.underwriting_decision.final_terms.tenure_months
        rate = detail.underwriting_decision.final_terms.annual_interest_rate_pct
        
    amount = math.floor(amount) if amount else 50000
    emi = math.floor(emi) if emi else int(amount / tenure * 1.05)

    def number_to_words(n):
        # Extremely basic number representation
        if n == 0: return "Zero"
        return f"{{n:,}}" 

    html_content = HTML_TEMPLATE.format(
        case_id_short=str(case_id)[:8].upper(),
        date_str=datetime.datetime.now().strftime("%d-%b-%Y"),
        store_name=kirana.store_name,
        owner_name=kirana.owner_name,
        district=kirana.location.district,
        state=kirana.location.state,
        pincode=kirana.location.pin_code or "XXXXXX",
        mobile=kirana.owner_mobile,
        amount=f"{{amount:,}}",
        amount_words=number_to_words(amount),
        tenure=tenure,
        rate=rate,
        emi=f"{{emi:,}}"
    )

    out_file = f"sanction_letter_{{str(case_id)[:8]}}.html"
    with open(out_file, "w") as f:
        f.write(html_content)
        
    print(f"Successfully generated HTML Sanction Letter: {{out_file}}")
    print(f"Open {{out_file}} in your browser to view or print as PDF.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="The UUID of the case to generate a sanction letter for")
    args = parser.parse_args()
    generate_sanction_letter(args.case_id)
