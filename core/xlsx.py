"""
Guardar la matriz sin perder las gráficas del 'Dashboard & Métricas'.

openpyxl no lee gráficas: al guardar un libro que las tiene, las elimina. guardar_con_graficas()
guarda con openpyxl y después vuelve a insertar en el .xlsx las gráficas y dibujos del archivo
original (xl/charts, xl/drawings, la relación de cada hoja y los Content-Types).
"""
import re
import zipfile
from pathlib import Path

NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
TIPO_DRAWING = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"
CT_DRAWING = "application/vnd.openxmlformats-officedocument.drawing+xml"
CT_CHART = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
# Elementos que en el XML de una hoja van DESPUÉS de <drawing> (orden del esquema CT_Worksheet)
_DESPUES_DE_DRAWING = ("<legacyDrawing", "<legacyDrawingHF", "<drawingHF", "<picture", "<oleObjects",
                       "<controls", "<webPublishItems", "<tableParts", "<extLst", "</worksheet>")


def _hojas(z):
    """{nombre de la hoja: ruta del xml} leyendo workbook.xml y sus relaciones."""
    wb = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    destino = {m.group(1): m.group(2) for m in re.finditer(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels)}
    destino.update({m.group(2): m.group(1) for m in re.finditer(r'<Relationship[^>]*Target="([^"]+)"[^>]*Id="([^"]+)"', rels)})
    hojas = {}
    for m in re.finditer(r'<sheet\b[^>]*>', wb):
        nombre = re.search(r'name="([^"]+)"', m.group(0)).group(1)
        rid = re.search(r'r:id="([^"]+)"', m.group(0)).group(1)
        hojas[nombre] = "xl/" + destino[rid].lstrip("/").removeprefix("xl/")
    return hojas


def _rels_de(ruta_hoja):
    p = Path(ruta_hoja)
    return (p.parent / "_rels" / f"{p.name}.rels").as_posix()


def _drawing_de_hoja(z, ruta_hoja):
    """Ruta del drawing de una hoja del libro original (o None)."""
    rels = _rels_de(ruta_hoja)
    if rels not in z.namelist():
        return None
    for m in re.finditer(r"<Relationship\b[^>]*>", z.read(rels).decode("utf-8")):
        if TIPO_DRAWING in m.group(0):
            target = re.search(r'Target="([^"]+)"', m.group(0)).group(1)
            return "xl/drawings/" + Path(target).name
    return None


def restaurar_graficas(original, destino):
    """Copia en 'destino' las gráficas/dibujos de 'original' (ambos .xlsx con las mismas hojas)."""
    with zipfile.ZipFile(original) as zo:
        hojas_o = _hojas(zo)
        dibujos = {n: _drawing_de_hoja(zo, r) for n, r in hojas_o.items()}
        dibujos = {n: d for n, d in dibujos.items() if d}
        if not dibujos:
            return
        partes = {n: zo.read(n) for n in zo.namelist() if n.startswith(("xl/charts/", "xl/drawings/"))}

    tmp = Path(destino).with_name(Path(destino).stem + ".tmp.xlsx")
    with zipfile.ZipFile(destino) as zd, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zn:
        hojas_d = _hojas(zd)
        cambios = {}
        for nombre, drawing in dibujos.items():
            hoja = hojas_d.get(nombre)
            if not hoja:
                continue
            rels = _rels_de(hoja)
            xml_rels = zd.read(rels).decode("utf-8") if rels in zd.namelist() else \
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{NS_REL}"></Relationships>'
            # Una sola relación de dibujo por hoja: se quitan las que haya dejado openpyxl y se apunta al original
            xml_rels = re.sub(rf'<Relationship\b[^>]*{re.escape(TIPO_DRAWING)}[^>]*/>', "", xml_rels)
            rid = "rIdGraficas1"
            xml_rels = xml_rels.replace("</Relationships>",
                                        f'<Relationship Id="{rid}" Type="{TIPO_DRAWING}" Target="../drawings/{Path(drawing).name}"/></Relationships>')
            xml_hoja = zd.read(hoja).decode("utf-8")
            xml_hoja = re.sub(r"<drawing\b[^>]*/>", "", xml_hoja)
            if 'xmlns:r="' not in xml_hoja[:2000]:
                xml_hoja = xml_hoja.replace("<worksheet ", '<worksheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
            pos = min(i for i in (xml_hoja.find(t) for t in _DESPUES_DE_DRAWING) if i >= 0)
            xml_hoja = xml_hoja[:pos] + f'<drawing r:id="{rid}"/>' + xml_hoja[pos:]
            cambios[hoja], cambios[rels] = xml_hoja.encode("utf-8"), xml_rels.encode("utf-8")

        ct = zd.read("[Content_Types].xml").decode("utf-8")
        for parte in partes:
            if parte.endswith(".xml") and "/_rels/" not in parte and f'PartName="/{parte}"' not in ct:
                tipo = CT_CHART if parte.startswith("xl/charts/") else CT_DRAWING
                ct = ct.replace("</Types>", f'<Override PartName="/{parte}" ContentType="{tipo}"/></Types>')
        cambios["[Content_Types].xml"] = ct.encode("utf-8")

        for item in zd.infolist():
            if item.filename in partes:
                continue
            zn.writestr(item, cambios.pop(item.filename, None) or zd.read(item.filename))
        for nombre, datos in {**cambios, **partes}.items():
            zn.writestr(nombre, datos)
    Path(tmp).replace(destino)


def guardar_con_graficas(wb, destino, original):
    wb.save(destino)
    restaurar_graficas(original, destino)
