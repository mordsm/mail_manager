import os
import sys
import re
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path("C:/workspace/llm_wiki")
DCM_GARDEN_DIR = Path("C:/workspace/domain_content_manager/vault/02 By Domain/Garden")
SOURCE_DOCX = ROOT_DIR / "raw/research/documents/tmp227a05_q.docx"
REAL_FILENAME = "המדריך_העירוני_לגינון_ביתי_טבעי.docx"
PROPER_RAW_PATH = ROOT_DIR / f"raw/research/documents/{REAL_FILENAME}"
ASSETS_DIR = ROOT_DIR / "wiki/assets/gardening"
OUTPUT_DIR = ROOT_DIR / "wiki/research/gardening"
MOCS_DIR = ROOT_DIR / "mocs"

def extract_docx_content(docx_path: Path):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DCM_GARDEN_DIR.mkdir(parents=True, exist_ok=True)
    MOCS_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(docx_path) as z:
        # Extract images
        image_count = 0
        for name in z.namelist():
            if name.startswith("word/media/"):
                img_name = Path(name).name
                target_img = ASSETS_DIR / img_name
                with open(target_img, "wb") as f_out, z.open(name) as f_in:
                    shutil.copyfileobj(f_in, f_out)
                image_count += 1
        print(f"Extracted {image_count} images into {ASSETS_DIR}")

        # Parse document.xml
        xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)

        paragraphs = []
        for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            pStyle = p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
            style_val = pStyle.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "") if pStyle is not None else ""
            
            p_text = "".join([node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]).strip()
            if p_text:
                paragraphs.append({
                    "style": style_val,
                    "text": p_text
                })

        return paragraphs, image_count

def segment_and_write_gardening_book(paragraphs, image_count):
    if not PROPER_RAW_PATH.exists() and SOURCE_DOCX.exists():
        shutil.copy2(SOURCE_DOCX, PROPER_RAW_PATH)
        print(f"Preserved proper raw file: {PROPER_RAW_PATH}")

    # Build full markdown book
    full_md_lines = [
        "---",
        "title: המדריך העירוני לגינון ביתי טבעי",
        "type: book",
        "domain: [garden, personal, research]",
        "tags: [book, gardening, urban_gardening, organic, soil, irrigation, companion_planting]",
        "status: active",
        "---",
        "",
        "# המדריך העירוני לגינון ביתי טבעי",
        "**מהדורה מתוקנת • איורים ייחודיים • אחד־עשר פרקים וחמישה נספחים**",
        "",
        "---",
        ""
    ]

    for p in paragraphs:
        style = p["style"]
        text = p["text"]

        if style in ["Title", "Subtitle"]:
            full_md_lines.append(f"# {text}\n")
        elif "Heading1" in style or style == "1" or re.match(r"^(פרק\s+\d+|נספח\s+[א-ת]|תוכן עניינים)", text):
            full_md_lines.append(f"\n## {text}\n")
        elif "Heading2" in style or style == "2":
            full_md_lines.append(f"\n### {text}\n")
        elif "Heading3" in style or style == "3":
            full_md_lines.append(f"\n#### {text}\n")
        else:
            full_md_lines.append(f"{text}\n")

    full_book_path = OUTPUT_DIR / "המדריך_העירוני_לגינון_ביתי_טבעי_ספר_שלם.md"
    full_book_text = "\n".join(full_md_lines)
    full_book_path.write_text(full_book_text, encoding="utf-8")
    
    # Also write full book copy to DCM Garden vault
    (DCM_GARDEN_DIR / "המדריך_העירוני_לגינון_ביתי_טבעי_ספר_שלם.md").write_text(full_book_text, encoding="utf-8")
    print(f"Wrote full gardening book: {full_book_path} ({len(full_md_lines)} lines)")

    # Mapping of sections
    sections_meta = {
        0: ("מבוא, עריכה ותוכן עניינים", "המדריך_העירוני_לגינון_00_מבוא_ותוכן.md", ["intro", "toc"]),
        1: ("פרק 1 — תשתיות, מצע ואדניות", "המדריך_העירוני_לגינון_פרק_01_תשתיות_מצע_ואדניות.md", ["soil", "containers", "drainage", "infrastructure"]),
        2: ("פרק 2 — בחירת צמחים: גילדות, שותפויות והתאמה מדויקת", "המדריך_העירוני_לגינון_פרק_02_בחירת_צמחים_וגילדות.md", ["plant_selection", "guilds", "companion_planting"]),
        3: ("פרק 3 — השקיה: פיזיולוגיית שורש ומשטרי מים חכמים", "המדריך_העירוני_לגינון_פרק_03_השקיה_ופיזיולוגיית_שורש.md", ["irrigation", "water", "root_physiology", "drip"]),
        4: ("פרק 4 — תזונה והגנה: דישון אורגני, קומפוסט ו־IPM", "המדריך_העירוני_לגינון_פרק_04_תזונה_קומפוסט_ו_ipm.md", ["nutrition", "organic_fertilizer", "compost", "ipm"]),
        5: ("פרק 5 — גידולים מיוחדים: גפן, זית, בננה ושיחי גדר", "המדריך_העירוני_לגינון_פרק_05_גידולים_מיוחדים.md", ["special_crops", "grape", "olive", "banana", "hedges"]),
        6: ("פרק 6 — מזיקים, מחלות ופתרון תקלות", "המדריך_העירוני_לגינון_פרק_06_מזיקים_מחלות_ופתרון_תקלות.md", ["pests", "diseases", "troubleshooting", "organic_control"]),
        7: ("פרק 7 — לוח שנה עונתי לגינה עירונית בישראל", "המדריך_העירוני_לגינון_פרק_07_לוח_שנה_עונתי.md", ["calendar", "seasons", "israel_climate", "planting_schedule"]),
        8: ("פרק 8 — אינדקס מורחב: 32 צמחים נבחרים", "המדריך_העירוני_לגינון_פרק_08_אינדקס_32_צמחים.md", ["plant_index", "herbs", "vegetables", "profiles"]),
        9: ("פרק 9 — מילון מושגים אגרונומי ואקולוגי", "המדריך_העירוני_לגינון_פרק_09_מילון_מושגים_אגרונומי.md", ["glossary", "agronomy", "ecology", "definitions"]),
        10: ("פרק 10 — ריבוי צמחים: ייחורים, הברכה וחלוקת גוש", "המדריך_העירוני_לגינון_פרק_10_ריבוי_צמחים_וייחורים.md", ["propagation", "cuttings", "layering", "division"]),
        11: ("פרק 11 — אינדקס נושאי מהיר", "המדריך_העירוני_לגינון_פרק_11_אינדקס_נושאי_מהיר.md", ["index", "quick_reference"]),
        101: ("נספח א׳ — גינון אנכי וניצול שטח", "המדריך_העירוני_לגינון_נספח_א_גינון_אנכי.md", ["vertical_gardening", "space_saving"]),
        102: ("נספח ב׳ — מאביקים וחרקים מועילים", "המדריך_העירוני_לגינון_נספח_ב_מאביקים_וחרקים_מועילים.md", ["pollinators", "beneficial_insects", "biodiversity"]),
        103: ("נספח ג׳ — יומן גינה", "המדריך_העירוני_לגינון_נספח_ג_יומן_גינה.md", ["garden_journal", "tracking", "logs"]),
        104: ("נספח ד׳ — היערכות למזג אוויר קיצוני", "המדריך_העירוני_לגינון_נספח_ד_היערכות_למזג_אוויר_קיצוני.md", ["extreme_weather", "heatwaves", "frost", "protection"]),
        105: ("נספח ה׳ — ערכת כלים ותחזוקה בסיסית", "המדריך_העירוני_לגינון_נספח_ה_ערכת_כלים_ותחזוקה.md", ["tools", "maintenance", "gear"])
    }

    current_key = 0
    buffers = {k: [] for k in sections_meta.keys()}

    for p in paragraphs:
        text = p["text"]

        m_ch = re.match(r"^פרק\s+(\d+)", text)
        m_app = re.match(r"^נספח\s+([א-ה])", text)

        if m_ch:
            num = int(m_ch.group(1))
            if num in sections_meta:
                current_key = num
        elif m_app:
            letter = m_app.group(1)
            letter_map = {"א": 101, "ב": 102, "ג": 103, "ד": 104, "ה": 105}
            if letter in letter_map:
                current_key = letter_map[letter]

        buffers[current_key].append(p)

    # Write each section file
    for key, paras in buffers.items():
        if not paras:
            continue
        title, filename, tags = sections_meta[key]

        ch_lines = [
            "---",
            f"title: \"{title}\"",
            "book: \"המדריך העירוני לגינון ביתי טבעי\"",
            f"section_key: {key}",
            "domain: [\"garden\", \"personal\"]",
            f"tags: {['gardening', 'urban_garden'] + tags}",
            f"sources: [\"raw/research/documents/{REAL_FILENAME}\"]",
            "type: book_chapter",
            "status: active",
            "---",
            "",
            f"# {title}",
            "**ספר:** [[המדריך_העירוני_לגינון_ביתי_טבעי_ספר_שלם|המדריך העירוני לגינון ביתי טבעי]] | **תחום:** גינון וקיימות ביתית",
            "",
            "---",
            ""
        ]

        for p in paras:
            st = p["style"]
            tx = p["text"]
            if "Heading1" in st or st == "1" or re.match(r"^(פרק\s+\d+|נספח\s+[א-ת])", tx):
                ch_lines.append(f"\n## {tx}\n")
            elif "Heading2" in st or st == "2":
                ch_lines.append(f"\n### {tx}\n")
            elif "Heading3" in st or st == "3":
                ch_lines.append(f"\n#### {tx}\n")
            else:
                ch_lines.append(f"{tx}\n")

        ch_lines.extend([
            "\n---",
            "### ניווט בספר הגינון:",
            "- 📖 [[המדריך_העירוני_לגינון_ביתי_טבעי_ספר_שלם|הספר המלא: המדריך העירוני לגינון]]",
            "- 🗺️ [[gardening_book_moc|מפת התוכן של ספר הגינון (MOC)]]"
        ])

        target_file = OUTPUT_DIR / filename
        target_file.write_text("\n".join(ch_lines), encoding="utf-8")
        
        # Also copy to DCM Garden folder
        (DCM_GARDEN_DIR / filename).write_text("\n".join(ch_lines), encoding="utf-8")
        print(f"Created: {filename} ({len(paras)} paras)")

    # Master MOC
    moc_content = f"""---
id: gardening-book-moc
title: "מפת תוכן: המדריך העירוני לגינון ביתי טבעי (Gardening Book MOC)"
created: "2026-10-18"
type: moc
domain: [garden, personal, research]
tags: [moc, gardening, urban_gardening, ecology]
---

# 🌿 מפת תוכן: המדריך העירוני לגינון ביתי טבעי
**מהדורה מתוקנת • איורים ייחודיים • אחד־עשר פרקים וחמישה נספחים**

## 📚 הספר המלא
- [[המדריך_העירוני_לגינון_ביתי_טבעי_ספר_שלם|המדריך העירוני לגינון ביתי טבעי (ספר שלם מאוחד)]]
- [[המדריך_העירוני_לגינון_00_מבוא_ותוכן|מבוא, הערת עריכה מקצועית ותוכן עניינים]]

---

## 🌻 פרקי הספר
- [[המדריך_העירוני_לגינון_פרק_01_תשתיות_מצע_ואדניות|פרק 1 — תשתיות, מצע ואדניות: המדריך המורחב (שורשים, ניקוז ואוורור)]]
- [[המדריך_העירוני_לגינון_פרק_02_בחירת_צמחים_וגילדות|פרק 2 — בחירת צמחים: גילדות, שותפויות והתאמה מדויקת]]
- [[המדריך_העירוני_לגינון_פרק_03_השקיה_ופיזיולוגיית_שורש|פרק 3 — השקיה: פיזיולוגיית שורש ומשטרי מים חכמים]]
- [[המדריך_העירוני_לגינון_פרק_04_תזונה_קומפוסט_ו_ipm|פרק 4 — תזונה והגנה: דישון אורגני, קומפוסט ו־IPM]]
- [[המדריך_העירוני_לגינון_פרק_05_גידולים_מיוחדים|פרק 5 — גידולים מיוחדים: גפן, זית, בננה ושיחי גדר]]
- [[המדריך_העירוני_לגינון_פרק_06_מזיקים_מחלות_ופתרון_תקלות|פרק 6 — מזיקים, מחלות ופתרון תקלות (הדברה אורגנית)]]
- [[המדריך_העירוני_לגינון_פרק_07_לוח_שנה_עונתי|פרק 7 — לוח שנה עונתי לגינה עירונית בישראל]]
- [[המדריך_העירוני_לגינון_פרק_08_אינדקס_32_צמחים|פרק 8 — אינדקס מורחב: 32 צמחים נבחרים]]
- [[המדריך_העירוני_לגינון_פרק_09_מילון_מושגים_אגרונומי|פרק 9 — מילון מושגים אגרונומי ואקולוגי]]
- [[המדריך_העירוני_לגינון_פרק_10_ריבוי_צמחים_וייחורים|פרק 10 — ריבוי צמחים: ייחורים, הברכה וחלוקת גוש]]
- [[המדריך_העירוני_לגינון_פרק_11_אינדקס_נושאי_מהיר|פרק 11 — אינדקס נושאי מהיר]]

---

## 🛠️ נספחים מעשיים
- [[המדריך_העירוני_לגינון_נספח_א_גינון_אנכי|נספח א׳ — גינון אנכי וניצול שטח]]
- [[המדריך_העירוני_לגינון_נספח_ב_מאביקים_וחרקים_מועילים|נספח ב׳ — מאביקים וחרקים מועילים]]
- [[המדריך_העירוני_לגינון_נספח_ג_יומן_גינה|נספח ג׳ — יומן גינה]]
- [[המדריך_העירוני_לגינון_נספח_ד_היערכות_למזג_אוויר_קיצוני|נספח ד׳ — היערכות למזג אוויר קיצוני]]
- [[המדריך_העירוני_לגינון_נספח_ה_ערכת_כלים_ותחזוקה|נספח ה׳ — ערכת כלים ותחזוקה בסיסית]]

---

## 🖼️ איורים ותרשימים
- {image_count} איורים מקצועיים נשמרו תחת `wiki/assets/gardening/` וזמינים לצפייה.
"""
    (MOCS_DIR / "gardening_book_moc.md").write_text(moc_content, encoding="utf-8")
    (DCM_GARDEN_DIR / "ספר_המדריך_העירוני_לגינון_ביתי_טבעי_MOC.md").write_text(moc_content, encoding="utf-8")
    print(f"Created Master Gardening MOC: {MOCS_DIR / 'gardening_book_moc.md'}")

if __name__ == "__main__":
    paras, img_count = extract_docx_content(SOURCE_DOCX)
    segment_and_write_gardening_book(paras, img_count)
    print("\n✅ Ingestion and structuring of Gardening Book completed successfully!")
