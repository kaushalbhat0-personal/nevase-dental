"""Fix document_service.py - repair indentation and syntax errors."""
import re

with open('backend/app/services/document_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# FIX 1: Fix the _build_encounter_summary_html broken return
# ============================================================
old_return = """{vitals_html}
{followup_html}
</div>

    return _build_html_document(body, branding=data.branding_context)"""

new_return = """{vitals_html}
{rx_html}
{followup_html}

    return _build_html_document(
        title=f"Encounter Summary - {data.patient_name}",
        body_html=body,
        meta=DocumentMeta(
            document_type=DocumentType.encounter_summary,
            tenant_id=data.tenant_id,
            resource_id=str(data.appointment_id),
        ),
        branding=branding,
    )"""

if old_return in content:
    content = content.replace(old_return, new_return)
    print("FIX 1: Fixed _build_encounter_summary_html return statement")
else:
    print("FIX 1: Could not find broken return statement")
    idx = content.find("{vitals_html}")
    if idx >= 0:
        print(f"  Found at {idx}: {repr(content[idx:idx+300])}")

# ============================================================
# FIX 2: Fix _css_template indentation and use string.Template
# ============================================================
# The _css_template has wrong indentation (8 spaces instead of 4)
# and uses .format() which conflicts with CSS values like "8px".
# Fix: correct indentation and use string.Template.

old_css_block = """    # Build CSS template — use .format() instead of f-string to avoid
    # Python 3.10 f-string parsing bug with number+letter combinations
    # like "15mm", "8px", "11px" inside f-strings with {{ }} escapes.
        _css_template = \"\"\"
        @page {{
            margin: {page_margin};
            @bottom-center {{
                content: \"Page \" counter(page) \" of \" counter(pages);
                font-size: 8px;
                color: #888;
            }}
        }}
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11px;
            line-height: 1.5;
            color: #222;
            margin: 0;
            padding: 0;
        }}
        .header {{
            border-bottom: 2px solid {primary};
            padding-bottom: 8px;
            margin-bottom: 12px;
        }}
        .header h1 {{
            font-size: 18px;
            color: {primary};
            margin: 0 0 4px 0;
        }}
        .header .clinic-info {{
            font-size: 10px;
            color: {secondary};
        }}
        .section {{
            margin-bottom: 12px;
        }}
        .section-title {{
            font-size: 12px;
            font-weight: bold;
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 3px;
            margin-bottom: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 5px 6px;
            text-align: left;
            font-size: 10px;
        }}
        th {{
            background-color: #f0f4ff;
            font-weight: bold;
            color: #333;
        }}
        .info-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .info-block {{
            flex: 1;
            min-width: 180px;
        }}
        .info-block label {{
            font-size: 9px;
            color: #888;
            text-transform: uppercase;
            display: block;
        }}
        .info-block .value {{
            font-size: 11px;
            font-weight: 500;
        }}
        .status-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }}
        .status-paid {{
            background-color: #d1fae5;
            color: #065f46;
        }}
        .status-unpaid {{
            background-color: #fee2e2;
            color: #991b1b;
        }}
        .total-row {{
            font-weight: bold;
            background-color: #f9fafb;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 8px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #888;
            text-align: center;
        }}
        .todo-placeholder {{
            border: 1px dashed {accent};
            background: #fffbeb;
            padding: 6px;
            margin: 6px 0;
            font-size: 9px;
            color: #92400e;
            border-radius: 3px;
        }}
        .vitals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 4px;
        }}
        .vital-item {{
            padding: 3px 6px;
            background: #f9fafb;
            border-radius: 3px;
        }}
        .vital-item label {{
            font-size: 8px;
            color: #888;
            display: block;
        }}
        .vital-item .value {{
            font-size: 11px;
            font-weight: 500;
        }}
        .soap-block {{
            margin-bottom: 8px;
        }}
        .soap-block .soap-label {{
            font-weight: bold;
            color: {primary};
            font-size: 10px;
        }}
        .soap-block .soap-content {{
            margin-left: 8px;
            white-space: pre-wrap;
        }}
        .prescription-item {{
            padding: 4px 0;
            border-bottom: 1px dotted #eee;
        }}
        .prescription-item:last-child {{
            border-bottom: none;
        }}
        .branding-logo {{
            max-height: 60px;
            max-width: 200px;
            margin-bottom: 6px;
        }}
        .branding-contact {{
            font-size: 9px;
            color: {secondary};
            margin-top: 2px;
        }}
        .branding-gst {{
            font-size: 9px;
            color: {secondary};
            margin-top: 1px;
        }}
        .branding-footer {{
            margin-top: 16px;
            padding-top: 6px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #666;
            text-align: center;
            font-style: italic;
        }}
        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 60px;
            opacity: 0.06;
            color: {primary};
            pointer-events: none;
            z-index: -1;
            white-space: nowrap;
        }}
    \"\"\""""

new_css_block = """    # Build CSS template — use string.Template to avoid
    # Python .format() parsing issues with CSS values like "8px", "11px".
    _css_template = \"\"\"
        @page {
            margin: $page_margin;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8px;
                color: #888;
            }
        }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11px;
            line-height: 1.5;
            color: #222;
            margin: 0;
            padding: 0;
        }
        .header {
            border-bottom: 2px solid $primary;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .header h1 {
            font-size: 18px;
            color: $primary;
            margin: 0 0 4px 0;
        }
        .header .clinic-info {
            font-size: 10px;
            color: $secondary;
        }
        .section {
            margin-bottom: 12px;
        }
        .section-title {
            font-size: 12px;
            font-weight: bold;
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 3px;
            margin-bottom: 6px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 5px 6px;
            text-align: left;
            font-size: 10px;
        }
        th {
            background-color: #f0f4ff;
            font-weight: bold;
            color: #333;
        }
        .info-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 8px;
        }
        .info-block {
            flex: 1;
            min-width: 180px;
        }
        .info-block label {
            font-size: 9px;
            color: #888;
            text-transform: uppercase;
            display: block;
        }
        .info-block .value {
            font-size: 11px;
            font-weight: 500;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }
        .status-paid {
            background-color: #d1fae5;
            color: #065f46;
        }
        .status-unpaid {
            background-color: #fee2e2;
            color: #991b1b;
        }
        .total-row {
            font-weight: bold;
            background-color: #f9fafb;
        }
        .footer {
            margin-top: 20px;
            padding-top: 8px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #888;
            text-align: center;
        }
        .todo-placeholder {
            border: 1px dashed $accent;
            background: #fffbeb;
            padding: 6px;
            margin: 6px 0;
            font-size: 9px;
            color: #92400e;
            border-radius: 3px;
        }
        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 4px;
        }
        .vital-item {
            padding: 3px 6px;
            background: #f9fafb;
            border-radius: 3px;
        }
        .vital-item label {
            font-size: 8px;
            color: #888;
            display: block;
        }
        .vital-item .value {
            font-size: 11px;
            font-weight: 500;
        }
        .soap-block {
            margin-bottom: 8px;
        }
        .soap-block .soap-label {
            font-weight: bold;
            color: $primary;
            font-size: 10px;
        }
        .soap-block .soap-content {
            margin-left: 8px;
            white-space: pre-wrap;
        }
        .prescription-item {
            padding: 4px 0;
            border-bottom: 1px dotted #eee;
        }
        .prescription-item:last-child {
            border-bottom: none;
        }
        .branding-logo {
            max-height: 60px;
            max-width: 200px;
            margin-bottom: 6px;
        }
        .branding-contact {
            font-size: 9px;
            color: $secondary;
            margin-top: 2px;
        }
        .branding-gst {
            font-size: 9px;
            color: $secondary;
            margin-top: 1px;
        }
        .branding-footer {
            margin-top: 16px;
            padding-top: 6px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #666;
            text-align: center;
            font-style: italic;
        }
        .watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 60px;
            opacity: 0.06;
            color: $primary;
            pointer-events: none;
            z-index: -1;
            white-space: nowrap;
        }
    \"\"\""""

if old_css_block in content:
    content = content.replace(old_css_block, new_css_block)
    print("FIX 2: Fixed _css_template indentation and switched to string.Template")
else:
    print("FIX 2: Could not find old CSS block")
    # Debug: find what's around _css_template
    idx = content.find('_css_template')
    if idx >= 0:
        print(f"  Found at {idx}: {repr(content[idx-50:idx+200])}")

# ============================================================
# FIX 3: Update _build_css return to use string.Template
# ============================================================
old_format = """    return _css_template.format(
        page_margin="15mm 12mm",
        primary=primary,
        secondary=secondary,
        accent=accent,
    )"""

new_format = """    from string import Template
    return Template(_css_template).safe_substitute(
        page_margin="15mm 12mm",
        primary=primary,
        secondary=secondary,
        accent=accent,
    )"""

if old_format in content:
    content = content.replace(old_format, new_format)
    print("FIX 3: Updated _build_css to use string.Template")
else:
    print("FIX 3: Could not find old format call")

# ============================================================
# Write the fixed content
# ============================================================
with open('backend/app/services/document_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nFile written: {len(content)} chars")

# Verify syntax
import py_compile
try:
    py_compile.compile('backend/app/services/document_service.py', doraise=True)
    print("SYNTAX CHECK: PASSED")
except py_compile.PyCompileError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")
