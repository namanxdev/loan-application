# -*- coding: utf-8 -*-
"""
PDF Generation Service using ReportLab

Generates sanction letter PDFs for approved loan applications.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Directory for generated PDFs
PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "pdfs")


def generate_sanction_letter(
    application_id: int,
    customer_name: str,
    loan_amount: int,
    tenure: int,
    credit_score: int,
    pan: str = "",
    income: int = 0
) -> str:
    """
    Generate a professional sanction letter PDF using ReportLab.
    
    Args:
        application_id: Unique application ID
        customer_name: Name of the customer
        loan_amount: Sanctioned loan amount
        tenure: Loan tenure in months
        credit_score: Customer's credit score
        pan: Customer's PAN number
        income: Customer's monthly income
        
    Returns:
        Path to the generated PDF file
    """
    # Ensure PDF directory exists
    os.makedirs(PDF_DIR, exist_ok=True)
    
    # Generate file path
    pdf_filename = f"{application_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d')
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2d3748')
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=12,
        leading=16
    )
    
    # Build document content
    elements = []
    
    # Company Header
    elements.append(Paragraph("NBFC LOAN SERVICES PVT. LTD.", title_style))
    elements.append(Paragraph("CIN: U65999MH2020PTC123456", header_style))
    elements.append(Paragraph("Registered Office: Financial District, Mumbai - 400001", header_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a365d')))
    elements.append(Spacer(1, 0.3*inch))
    
    # Document title
    elements.append(Paragraph("<b>LOAN SANCTION LETTER</b>", 
                              ParagraphStyle('DocTitle', parent=title_style, fontSize=16)))
    elements.append(Spacer(1, 0.2*inch))
    
    # Reference and Date
    ref_date_data = [
        [f"Reference No: LOAN-{application_id:06d}", 
         f"Date: {datetime.now().strftime('%B %d, %Y')}"]
    ]
    ref_table = Table(ref_date_data, colWidths=[3*inch, 3*inch])
    ref_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(ref_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Greeting
    elements.append(Paragraph(f"Dear <b>{customer_name}</b>,", body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Body text
    elements.append(Paragraph(
        "We are pleased to inform you that your loan application has been "
        "<b>APPROVED</b> based on our credit assessment and underwriting criteria.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Loan Details Table
    elements.append(Paragraph("<b>LOAN DETAILS:</b>", body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Calculate EMI (simplified formula)
    rate = 0.01  # 12% annual = 1% monthly
    if rate > 0 and tenure > 0:
        emi = (loan_amount * rate * (1 + rate)**tenure) / ((1 + rate)**tenure - 1)
    else:
        emi = loan_amount / max(tenure, 1)
    
    loan_data = [
        ["Particulars", "Details"],
        ["Application ID", str(application_id)],
        ["Applicant Name", customer_name],
        ["PAN Number", pan if pan else "N/A"],
        ["Sanctioned Amount", f"Rs. {loan_amount:,}"],
        ["Loan Tenure", f"{tenure} months"],
        ["Interest Rate", "12% per annum"],
        ["EMI Amount", f"Rs. {emi:,.2f}"],
        ["Credit Score", str(credit_score)],
    ]
    
    loan_table = Table(loan_data, colWidths=[2.5*inch, 3.5*inch])
    loan_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        
        # Alternating row colors
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#f7fafc')),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(loan_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms and conditions
    elements.append(Paragraph("<b>TERMS AND CONDITIONS:</b>", body_style))
    terms = [
        "1. This sanction is valid for 30 days from the date of issue.",
        "2. Disbursement is subject to completion of all documentation.",
        "3. The sanctioned amount may be revised based on final verification.",
        "4. Interest rate is subject to change as per RBI guidelines.",
        "5. Pre-closure charges may apply as per the loan agreement.",
    ]
    for term in terms:
        elements.append(Paragraph(term, ParagraphStyle('Terms', parent=body_style, fontSize=10, leftIndent=20)))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Next steps
    elements.append(Paragraph(
        "Please visit our nearest branch with this letter and the required documents "
        "to complete the disbursement process.",
        body_style
    ))
    elements.append(Spacer(1, 0.4*inch))
    
    # Signature section
    elements.append(Paragraph("Yours sincerely,", body_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("<b>Authorized Signatory</b>", body_style))
    elements.append(Paragraph("NBFC Loan Services Pvt. Ltd.", body_style))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e0')))
    elements.append(Spacer(1, 0.1*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, 
                                   alignment=TA_CENTER, textColor=colors.gray)
    elements.append(Paragraph(
        "This is a system-generated document. For queries, contact: support@nbfcloans.com | "
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path


def get_pdf_path(application_id: int) -> str:
    """
    Get the path to a sanction letter PDF.
    
    Args:
        application_id: Application ID
        
    Returns:
        Full path to the PDF file
    """
    return os.path.join(PDF_DIR, f"{application_id}.pdf")


def pdf_exists(application_id: int) -> bool:
    """
    Check if a sanction letter PDF exists.
    
    Args:
        application_id: Application ID
        
    Returns:
        True if PDF exists, False otherwise
    """
    return os.path.exists(get_pdf_path(application_id))
