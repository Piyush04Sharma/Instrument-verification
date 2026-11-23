import io

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#14213D")
BRASS = colors.HexColor("#B8892B")
GREY = colors.HexColor("#5A6678")


def build_certificate_pdf(certificate, verify_url):
    """Return the bytes of an A4 landscape certificate with a QR code to the public check page."""
    application = certificate.application
    instrument = application.instrument
    owner = application.applicant
    profile = getattr(owner, "profile", None)
    shop = (profile.shop_name if profile and profile.shop_name else owner.get_full_name()) or owner.username

    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))
    c.setTitle(f"Certificate {certificate.number}")

    # Double border
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.rect(12 * mm, 12 * mm, page_w - 24 * mm, page_h - 24 * mm)
    c.setStrokeColor(BRASS)
    c.setLineWidth(0.8)
    c.rect(15 * mm, 15 * mm, page_w - 30 * mm, page_h - 30 * mm)

    # Ruler ticks hanging from the top of the inner border
    c.setStrokeColor(BRASS)
    c.setLineWidth(0.6)
    x = 20 * mm
    i = 0
    top = page_h - 15 * mm
    while x <= page_w - 20 * mm:
        length = 4 * mm if i % 10 == 0 else (2.6 * mm if i % 5 == 0 else 1.5 * mm)
        c.line(x, top, x, top - length)
        x += 2 * mm
        i += 1

    # Heading
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 30)
    c.drawCentredString(page_w / 2, page_h - 42 * mm, "Certificate of Verification")
    c.setFont("Helvetica", 11)
    c.setFillColor(GREY)
    c.drawCentredString(
        page_w / 2, page_h - 51 * mm,
        "Weighing and measuring instrument verified through the Online Verification System",
    )

    # Details
    rows = [
        ("Certificate number", certificate.number),
        ("Instrument", f"{instrument.category.name}: {instrument.make} {instrument.model_number}"),
        ("Serial number", instrument.serial_number),
        ("Capacity and class", f"{instrument.capacity.normalize():f} {instrument.unit}, class {instrument.accuracy_class}"),
        ("Owner", shop),
        ("Place of use", instrument.location_of_use),
        ("Date of verification", certificate.issued_on.strftime("%d %B %Y")),
        ("Valid until", certificate.valid_until.strftime("%d %B %Y")),
    ]
    y = page_h - 68 * mm
    for label, value in rows:
        c.setFont("Helvetica", 10)
        c.setFillColor(GREY)
        c.drawString(32 * mm, y, label)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(NAVY)
        c.drawString(82 * mm, y, str(value)[:70])
        y -= 9 * mm

    # QR code
    size = 34 * mm
    widget = QrCodeWidget(verify_url)
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    drawing.add(widget)
    qr_x, qr_y = page_w - 32 * mm - size, 30 * mm
    renderPDF.draw(drawing, c, qr_x, qr_y)
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawCentredString(qr_x + size / 2, qr_y - 5 * mm, "Scan to check this certificate online")

    # Footer
    officer = certificate.issued_by
    officer_name = (officer.get_full_name() or officer.username) if officer else "Inspection officer"
    c.setFont("Helvetica", 10)
    c.setFillColor(NAVY)
    c.drawString(32 * mm, 36 * mm, f"Issued by: {officer_name}")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    c.drawString(32 * mm, 28 * mm, f"Check authenticity at {verify_url}")

    c.showPage()
    c.save()
    return buffer.getvalue()
