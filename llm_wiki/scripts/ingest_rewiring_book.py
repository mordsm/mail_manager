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
SOURCE_DOCX = ROOT_DIR / "raw/research/documents/tmp3gxrng5g.docx"
REAL_FILENAME = "חיווט_מחדש_ספר_מאוחד_מתוקן_סופי_v3.docx"
PROPER_RAW_PATH = ROOT_DIR / f"raw/research/documents/{REAL_FILENAME}"
ASSETS_DIR = ROOT_DIR / "wiki/assets/rewiring"
OUTPUT_DIR = ROOT_DIR / "wiki/research/rewiring"
MOCS_DIR = ROOT_DIR / "mocs"

def extract_docx_content(docx_path: Path):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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

        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        
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

        return paragraphs

def segment_and_write_book(paragraphs):
    # Copy raw to proper filename
    if not PROPER_RAW_PATH.exists() and SOURCE_DOCX.exists():
        shutil.copy2(SOURCE_DOCX, PROPER_RAW_PATH)
        print(f"Preserved proper raw file: {PROPER_RAW_PATH}")

    # Build full markdown book
    full_md_lines = [
        "---",
        "title: חיווט מחדש – להבין את המכונה האנושית מניורונים ועד תנועה",
        "author: משה שרון",
        "year: 2026",
        "type: book",
        "domain: [research, personal, health]",
        "tags: [book, neuroscience, somatic, vagus_nerve, dopamine, breathing, movement]",
        "status: active",
        "---",
        "",
        "# חיווט מחדש – להבין את המכונה האנושית מניורונים ועד תנועה",
        "**מאת:** משה שרון | **מהדורה:** 2026",
        "",
        "---",
        ""
    ]

    for p in paragraphs:
        style = p["style"]
        text = p["text"]

        if style in ["Title", "Subtitle"]:
            full_md_lines.append(f"# {text}\n")
        elif "Heading1" in style or style == "1" or re.match(r"^(שער\s+[א-ת]|פרק\s+\d+)", text):
            full_md_lines.append(f"\n## {text}\n")
        elif "Heading2" in style or style == "2":
            full_md_lines.append(f"\n### {text}\n")
        elif "Heading3" in style or style == "3":
            full_md_lines.append(f"\n#### {text}\n")
        else:
            full_md_lines.append(f"{text}\n")

    full_book_path = OUTPUT_DIR / "חיווט_מחדש_ספר_שלם.md"
    full_book_path.write_text("\n".join(full_md_lines), encoding="utf-8")
    print(f"Wrote full book: {full_book_path} ({len(full_md_lines)} lines)")

    # Segment into distinct chapters
    chapters = []
    current_chapter = {
        "id": "intro",
        "title": "פתח דבר ומבוא",
        "gate": "מבוא",
        "lines": []
    }

    chapter_mapping = {
        1: ("פרק 1 — הקוקטייל הכימי של המוח", "שער א׳ – הבסיס", ["דופמין", "סרוטונין", "GABA", "מקלחות קרות", "הומאוסטזיס"]),
        2: ("פרק 2 — מערכת העצבים: חדר הבקרה שלא מפסיק לעבוד", "שער א׳ – הבסיס", ["מערכת העצבים", "העצב התועה", "אמיגדלה", "וגאלי", "ויסות"]),
        3: ("פרק 3 — גמישות מוחית: המוח שמשנה את עצמו", "שער א׳ – הבסיס", ["נוירופלסטיות", "גמישות מוחית", "למידה", "חיווט מחדש"]),
        4: ("פרק 4 — מדע הנשימה: השלטים הנסתרים של לוח המכוונים", "שער ב׳ – ויסות גוף–מוח", ["נשימה", "CO2", "חמצן", "ויסות עצבי", "סרעפת"]),
        5: ("פרק 5 — EVOP בחיים האמיתיים", "שער ב׳ – ויסות גוף–מוח", ["EVOP", "פרוטוקול ויסות", "עוררות", "איזון"]),
        6: ("פרק 6 — ציר המעי–מוח והמיקרוביום — המנגנונים", "שער ב׳ – ויסות גוף–מוח", ["ציר מעי מוח", "מיקרוביום", "בוטיראט", "סרוטונין במעי"]),
        7: ("פרק 7 — טראומה, ניבוי פעיל וניעור סומטי", "שער ב׳ – ויסות גוף–מוח", ["טראומה", "ניעור סומטי", "מודל ניבוי", "גוף"]),
        8: ("פרק 8 — הקיבה שיודעת הרבה — אבל לא הכול", "שער ב׳ – ויסות גוף–מוח", ["אינטרוספציה", "תחושות בטן", "קיבה"]),
        9: ("פרק 9 — השריר שמדבר עם המוח", "שער ג׳ – תנועה כתרופה", ["שרירים", "מיוקינים", "תנועה", "פעילות גופנית"]),
        10: ("פרק 10 — פסיכותרפיה סומטית: כשהגוף נכנס לחדר הטיפול", "שער ג׳ – תנועה כתרופה", ["פסיכותרפיה סומטית", "טיפול גוף נפש", "הקשבה לתחושות"]),
        11: ("פרק 11 — יוגה והמערכת העצבית: הרבה יותר ממתיחה טובה", "שער ג׳ – תנועה כתרופה", ["יוגה", "מערכת העצבים", "ויסות", "נשימה"]),
        12: ("פרק 12 — טאי צ'י: מדיטציה בתנועה וכיול שיווי המשקל", "שער ג׳ – תנועה כתרופה", ["טאי צ'י", "שיווי משקל", "מדיטציה בתנועה"]),
        13: ("פרק 13 — צ'י קונג ומיקרו־תנועה: מהמסורת אל הגוף המודרני", "שער ג׳ – תנועה כתרופה", ["צ'י קונג", "מיקרו תנועה", "אנרגיה וויסות"]),
        14: ("פרק 14 — מפת הדרכים: איך מחברים את הכול לחיים אמיתיים", "שער ד׳ – אינטגרציה", ["אינטגרציה", "פרוטוקולים", "אורח חיים", "מפת דרכים"])
    }

    # Split lines by chapter markers
    current_num = 0
    chapter_buffers = {i: [] for i in range(15)} # 0: intro, 1..14

    for p in paragraphs:
        text = p["text"]
        m = re.match(r"^פרק\s+(\d+)", text)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 14:
                current_num = num

        chapter_buffers[current_num].append(p)

    # Write each chapter file
    for num, paras in chapter_buffers.items():
        if not paras:
            continue
        if num == 0:
            ch_title = "חיווט מחדש – פתח דבר ומבוא"
            gate = "שער א׳ – הבסיס"
            tags = ["intro", "rewiring", "neuroscience"]
            filename = "חיווט_מחדש_00_פתח_דבר_ומבוא.md"
        else:
            meta = chapter_mapping.get(num, (f"פרק {num}", "כללי", ["rewiring"]))
            ch_title = meta[0]
            gate = meta[1]
            tags = ["rewiring", "neuroscience"] + meta[2]
            filename = f"חיווט_מחדש_פרק_{num:02d}.md"

        ch_lines = [
            "---",
            f"title: \"{ch_title}\"",
            f"book: \"חיווט מחדש\"",
            f"chapter: {num}",
            f"gate: \"{gate}\"",
            f"author: \"משה שרון\"",
            f"domain: [\"research\", \"personal\"]",
            f"tags: {tags}",
            f"sources: [\"raw/research/documents/{REAL_FILENAME}\"]",
            "type: book_chapter",
            "status: active",
            "---",
            "",
            f"# {ch_title}",
            f"**ספר:** [[חיווט מחדש]] | **שער:** {gate} | **מאת:** משה שרון",
            "",
            "---",
            ""
        ]

        for p in paras:
            st = p["style"]
            tx = p["text"]
            if "Heading1" in st or st == "1" or re.match(r"^פרק\s+\d+", tx):
                ch_lines.append(f"\n## {tx}\n")
            elif "Heading2" in st or st == "2":
                ch_lines.append(f"\n### {tx}\n")
            elif "Heading3" in st or st == "3":
                ch_lines.append(f"\n#### {tx}\n")
            else:
                ch_lines.append(f"{tx}\n")

        # Add cross references
        prev_num = num - 1 if num > 0 else None
        next_num = num + 1 if num < 14 else None
        nav_lines = ["\n---", "### ניווט בספר:", f"- 📖 [[חיווט_מחדש_ספר_שלם|הספר המלא: חיווט מחדש]]", f"- 🗺️ [[rewiring_book_moc|מפת התוכן של הספר (MOC)]]"]
        if prev_num is not None:
            prev_file = "חיווט_מחדש_00_פתח_דבר_ומבוא" if prev_num == 0 else f"חיווט_מחדש_פרק_{prev_num:02d}"
            nav_lines.append(f"- ⬅️ פרק קודם: [[{prev_file}]]")
        if next_num is not None:
            next_file = f"חיווט_מחדש_פרק_{next_num:02d}"
            nav_lines.append(f"- ➡️ פרק הבא: [[{next_file}]]")

        ch_lines.extend(nav_lines)

        target_file = OUTPUT_DIR / filename
        target_file.write_text("\n".join(ch_lines), encoding="utf-8")
        print(f"Created: {target_file.name} ({len(paras)} paragraphs)")

    # Build Master MOC
    moc_content = f"""---
id: rewiring-book-moc
title: "מפת תוכן: ספר חיווט מחדש (Rewiring Book MOC)"
created: "2026-10-18"
type: moc
domain: [research, personal, health]
tags: [moc, rewiring, neuroscience, somatic]
---

# 📖 מפת תוכן: ספר חיווט מחדש
**להבין את המכונה האנושית מניורונים ועד תנועה**
**מאת:** משה שרון | **מהדורה מלאה:** 2026

## 📚 הספר המלא
- [[חיווט_מחדש_ספר_שלם|הספר המלא (קובץ מאוחד)]]
- [[חיווט_מחדש_00_פתח_דבר_ומבוא|פתח דבר – המדריך למשתמש במכונה האנושית]]

---

## 🏛️ שער א׳ – הבסיס
- [[חיווט_מחדש_פרק_01|פרק 1 — הקוקטייל הכימי של המוח (דופמין, סרוטונין, GABA, מקלחות קרות, הומאוסטזיס)]]
- [[חיווט_מחדש_פרק_02|פרק 2 — מערכת העצבים: חדר הבקרה שלא מפסיק לעבוד (העצב התועה, אמיגדלה, ויסות)]]
- [[חיווט_מחדש_פרק_03|פרק 3 — גמישות מוחית: המוח שמשנה את עצמו (נוירופלסטיות)]]

## 🧘 שער ב׳ – ויסות גוף–מוח
- [[חיווט_מחדש_פרק_04|פרק 4 — מדע הנשימה: השלטים הנסתרים של לוח המכוונים האנושי]]
- [[חיווט_מחדש_פרק_05|פרק 5 — EVOP בחיים האמיתיים (פרוטוקול ויסות עוררות)]]
- [[חיווט_מחדש_פרק_06|פרק 6 — ציר המעי–מוח והמיקרוביום — המנגנונים]]
- [[חיווט_מחדש_פרק_07|פרק 7 — טראומה, ניבוי פעיל וניעור סומטי]]
- [[חיווט_מחדש_פרק_08|פרק 8 — הקיבה שיודעת הרבה — אבל לא הכול (אינטרוספציה)]]

## 🏃 שער ג׳ – תנועה כתרופה
- [[חיווט_מחדש_פרק_09|פרק 9 — השריר שמדבר עם המוח (מיוקינים ופעילות גופנית)]]
- [[חיווט_מחדש_פרק_10|פרק 10 — פסיכותרפיה סומטית: כשהגוף נכנס לחדר הטיפול]]
- [[חיווט_מחדש_פרק_11|פרק 11 — יוגה והמערכת העצבית: הרבה יותר ממתיחה טובה]]
- [[חיווט_מחדש_פרק_12|פרק 12 — טאי צ'י: מדיטציה בתנועה וכיול שיווי המשקל]]
- [[חיווט_מחדש_פרק_13|פרק 13 — צ'י קונג ומיקרו־תנועה: מהמסורת אל הגוף המודרני]]

## 🌟 שער ד׳ – אינטגרציה
- [[חיווט_מחדש_פרק_14|פרק 14 — מפת הדרכים: איך מחברים את הכול לחיים אמיתיים (פרוטוקולים והרגלים)]]

---

## 🖼️ אינפוגרפיקות ומדיה
- 76 אינפוגרפיקות ואיורים מקצועיים נשמרו תחת `wiki/assets/rewiring/` וזמינים לצפייה.
"""
    (MOCS_DIR / "rewiring_book_moc.md").write_text(moc_content, encoding="utf-8")
    print(f"Created Master MOC: {MOCS_DIR / 'rewiring_book_moc.md'}")

    # Clean up false stub notes
    stubs_to_remove = [
        ROOT_DIR / "wiki/research/topics/tmp3gxrng5g.md",
        ROOT_DIR / "wiki/research/topics/tmp227a05-q.md",
        ROOT_DIR / "wiki/research/contradictions/source-binary-asset.md"
    ]
    for stub in stubs_to_remove:
        if stub.exists():
            stub.unlink()
            print(f"Removed misleading stub file: {stub.name}")

if __name__ == "__main__":
    paras = extract_docx_content(SOURCE_DOCX)
    segment_and_write_book(paras)
    print("\n✅ Ingestion and structuring of 'חיווט מחדש' completed successfully!")
