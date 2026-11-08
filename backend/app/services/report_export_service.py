"""Dependency-free PDF and XLSX rendering for tenant-scoped report metrics."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import re
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


REPORT_LABELS = {
    "ventas": "Reporte de ventas",
    "productos": "Reporte de productos y categorias",
    "sucursales": "Rendimiento de sucursales",
    "inventario": "Reporte de inventario y reservas",
    "tendencias": "Tendencias de ventas",
}


def _totals(report_type: str, metrics: dict) -> list[tuple[str, Any]]:
    if report_type == "ventas":
        return [("Total ventas pagadas", metrics.get("ventas_pagadas", 0)),
                ("Total pedidos pagados", metrics.get("pedidos_pagados", 0))]
    if report_type == "productos":
        products = metrics.get("productos_mas_vendidos", [])
        return [
            ("Total unidades vendidas", sum((row.get("unidades", 0) for row in products), 0)),
            ("Total ingresos de productos", sum(
                (Decimal(str(row.get("ingresos", 0))) for row in products), Decimal("0")
            )),
        ]
    if report_type == "sucursales":
        branches = metrics.get("rendimiento_por_sucursal", [])
        return [
            ("Total ventas pagadas", sum(
                (Decimal(str(row.get("ventas_pagadas", row.get("ingresos_netos", 0)))) for row in branches), Decimal("0")
            )),
            ("Total pedidos pagados", sum((row.get("pedidos_pagados", row.get("cantidad_ventas", 0)) for row in branches), 0)),
        ]
    if report_type == "inventario":
        return [("Total stock disponible", metrics.get("stock_disponible_total", 0)),
                ("Total unidades reservadas", metrics.get("unidades_reservadas", 0))]
    current = metrics.get("periodo_actual", {})
    return [("Ventas pagadas del periodo actual", current.get("ventas_pagadas", 0)),
            ("Pedidos pagados del periodo actual", current.get("pedidos_pagados", 0))]


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = f"{prefix} / {key}" if prefix else str(key)
            rows.extend(_flatten(item, label))
    elif isinstance(value, list):
        if not value:
            rows.append((prefix, "Sin datos"))
        for index, item in enumerate(value, 1):
            rows.extend(_flatten(item, f"{prefix} {index}"))
    else:
        rows.append((prefix, value))
    return rows


def _safe_filename(report_type: str, start: date, end: date, extension: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", report_type.lower()).strip("-")
    return f"fashionstore-{slug}-{start.isoformat()}-{end.isoformat()}.{extension}"


def _xlsx(title: str, start: date, end: date, branch: str, metrics: dict,
          organization_name: str | None = None, generated_at: datetime | None = None) -> bytes:
    rows: list[list[Any]] = [
        [title],
        *([["Empresa", organization_name]] if organization_name else []),
        ["Periodo", f"{start.isoformat()} a {end.isoformat()}"],
        ["Sucursal", branch or "Todas las sucursales"],
        ["Generado", (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()],
        [],
        ["Metrica", "Valor"],
    ]
    rows.extend([[label, value] for label, value in _flatten(metrics)])
    rows.extend([[], ["Totales"], *_totals_for_sheet(title, metrics)])

    def cell_xml(value: Any, cell_ref: str) -> str:
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            return f'<c r="{cell_ref}"><v>{escape(str(value))}</v></c>'
        text = "" if value is None else str(value)
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
            return f'<c r="{cell_ref}"><v>{text}</v></c>'
        return f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'

    xml_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = "".join(cell_xml(value, f"{'AB'[column_index]}{row_index}")
                        for column_index, value in enumerate(row[:2]))
        xml_rows.append(f'<row r="{row_index}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Reporte" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>""")
        archive.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>""")
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>""")
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def _totals_for_sheet(title: str, metrics: dict) -> list[list[Any]]:
    report_type = next((key for key, label in REPORT_LABELS.items() if label == title), "ventas")
    return [[label, value] for label, value in _totals(report_type, metrics)]


def _pdf(title: str, start: date, end: date, branch: str, metrics: dict,
         organization_name: str | None = None, generated_at: datetime | None = None) -> bytes:
    lines = [title, f"Periodo: {start.isoformat()} a {end.isoformat()}",
             *([f"Empresa: {organization_name}"] if organization_name else []),
             f"Sucursales: {branch or 'Todas las sucursales'}",
             f"Generado: {(generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()}",
             "", "Metricas calculadas"]
    lines.extend(f"{label}: {value}" for label, value in _flatten(metrics))
    lines.extend(["", "Totales"])
    lines.extend(f"{label}: {value}" for label, value in _totals(
        next((key for key, label in REPORT_LABELS.items() if label == title), "ventas"), metrics
    ))
    lines = [line.encode("cp1252", errors="replace").decode("cp1252")[:115] for line in lines]
    pages = [lines[index:index + 48] for index in range(0, max(1, len(lines)), 48)]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{4 + index * 2} 0 R' for index in range(len(pages)))}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for index, page_lines in enumerate(pages):
        page_id = 4 + index * 2
        stream_id = page_id + 1
        commands = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for line in page_lines:
            commands.append(f"<{line.encode('cp1252', errors='replace').hex().upper()}> Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(output)


def build_report_export(
    format_name: str, report_type: str, start: date, end: date,
    branch: str, metrics: dict, organization_name: str | None = None,
    generated_at: datetime | None = None,
) -> tuple[bytes, str, str]:
    """Render already tenant-filtered server metrics to PDF or XLSX."""
    title = REPORT_LABELS[report_type]
    if format_name == "pdf":
        return _pdf(title, start, end, branch, metrics, organization_name, generated_at), "application/pdf", _safe_filename(report_type, start, end, "pdf")
    return (
        _xlsx(title, start, end, branch, metrics, organization_name, generated_at),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _safe_filename(report_type, start, end, "xlsx"),
    )
