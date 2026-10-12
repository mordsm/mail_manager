import json
import re
import urllib.parse
from pathlib import Path

def generate_perfect_website():
    root_dir = Path(".")
    book_dir = root_dir / "wiki" / "research" / "books" / "inner_gate"
    site_dir = root_dir / "site" / "inner_gate"
    assets_dir = site_dir / "assets" / "gut_images"

    # Map image filenames to exact chapter sections
    image_mappings = {
        # Chapter 1
        1: [
            {"match_sec": "1.1", "filename": "פרק_1_image3.jpg", "title": "תרשים 1.1: אנטומיה ומפת מסע המזון במערכת העיכול"}
        ],
        # Chapter 2
        2: [
            {"match_sec": "2.1", "filename": "פרק_2_image4.png", "title": "תרשים 2.1: מפת הקהילה המיקרוביאלית במעי"},
            {"match_sec": "2.2", "filename": "פרק_2_image5.jpg", "title": "איור 2.2: מבנה מחסום המעי, תאי אפיתל וחיבורים הדוקים (Tight Junctions)"},
            {"match_sec": "2.3", "filename": "פרק_2_image6.jpg", "title": "איור 2.3: תסיסת סיבים וייצור חומצות שומן קצרות שרשרת (בוטיראט, אצטט, פרופיונאט)"},
            {"match_sec": "2.5", "filename": "פרק_2_2.5המדריך_המעשי_למזונות_מותססים_image7.jpg", "title": "איור 2.5: גלריית מזונות מותססים — כרוב כבוש, קימצ׳י, קפיר, יוגורט וקומבוצ׳ה"}
        ],
        # Chapter 3
        3: [
            {"match_sec": "3.1", "filename": "פרק_3_image8.jpg", "title": "תרשים 3.1: סיבים פרה-ביוטיים והזנת חיידקי המעי"},
            {"match_sec": "3.3", "filename": "פרק_3_image9.jpg", "title": "תרשים 3.3: עקרונות התזונה הים-תיכונית הירוקה, פוליפנולים ומנקאי"}
        ],
        # Chapter 4
        4: [
            {"match_sec": "4.1", "filename": "פרק_4_image10.jpg", "title": "תרשים 4.1: מבנה צלחת מאוזנת ושילוב דגנים וקטניות"}
        ],
        # Chapter 5
        5: [
            {"match_sec": "5.1", "filename": "פרק_5_image11.jpg", "title": "תרשים 5.1: מפת התסמינים העיכוליים — מה שכיח ומה מצדיק בירור"},
            {"match_sec": "5.2", "filename": "פרק_5_image12.png", "title": "תרשים 5.2: מנגנוני נפיחות וגזים במערכת העיכול"},
            {"match_sec": "5.3", "filename": "פרק_5_image13.png", "title": "תרשים 5.3: עצירות — סוגי סיבים ונוזלים"},
            {"match_sec": "5.5", "filename": "פרק_5_image14.png", "title": "תרשים 5.5: תסמונת המעי הרגיז (IBS) והנחיות קליניות"},
            {"match_sec": "5.6", "filename": "פרק_5_image15.png", "title": "תרשים 5.6: דיאטת FODMAP דלת תסיסה — שלבי היישום והחזרה לתזונה"}
        ],
        # Chapter 6
        6: [
            {"match_sec": "6.1", "filename": "פרק_6_image16.jpg", "title": "תרשים 6.1: בדיקות מעבדה, קלפרוטקטין, בדיקות צואה ואנדוסקופיה"}
        ],
        # Chapter 7
        7: [
            {"match_sec": "7.1", "filename": "פרק_7_image17.jpg", "title": "תרשים 7.1: השפעת תרופות (PPI, NSAIDs) ותוספים על סביבת המעי"}
        ],
        # Chapter 8
        8: [
            {"match_sec": "8.1", "filename": "פרק_8_image18.jpg", "title": "תרשים 8.1: בריאות המעי במעגלי החיים — גיל מבוגר, הריון וילדים"}
        ],
        # Chapter 9
        9: [
            {"match_sec": "9.1", "filename": "פרק_9_image19.jpg", "title": "תרשים 9.1: ציר המעי–מוח (Gut-Brain Axis), סרוטונין ועייפות כרונית"}
        ],
        # Chapter 10
        10: [
            {"match_sec": "10.1", "filename": "פרק_10_10.1השעון_הצירקדי_מי_מכוון_את_הגוף_image21.png", "title": "תרשים 10.1: השעון הצירקדי הביולוגי ותזמון הארוחות"},
            {"match_sec": "10.5", "filename": "פרק_10_image20.png", "title": "תרשים 10.5: אכילה מוגבלת בזמן (16:8 TRE) ומטבוליזם לילי"}
        ],
        # Chapter 11
        11: [
            {"match_sec": "11.1", "filename": "פרק_11_image22.png", "title": "תרשים 11.1: תזמון רכיבים תזונתיים וביצועים"},
            {"match_sec": "11.2", "filename": "פרק_11_image23.png", "title": "תרשים 11.2: השפעת קפאין על ערנות ופינוי קיבה"}
        ],
        # Chapter 12
        12: [
            {"match_sec": "12.1", "filename": "פרק_12_image24.jpg", "title": "תרשים 12.1: קשרי הגומלין בין איכות השינה, מדדי לחץ ובריאות המעי"}
        ],
        # Chapter 13
        13: [
            {"match_sec": "13.1", "filename": "פרק_13_image25.jpg", "title": "תרשים 13.1: תנועתיות מעיים, הליכה וניהול מאמץ (Pacing)"}
        ],
        # Chapter 14
        14: [
            {"match_sec": "14.1", "filename": "פרק_14_image26.jpg", "title": "תרשים 14.1: פסיכולוגיה של שינוי הרגלים, הרגלים אטומיים ו-Tiny Habits"}
        ],
        # Chapter 15
        15: [
            {"match_sec": "15.1", "filename": "פרק_15_image27.jpg", "title": "תרשים 15.1: יומן טריגרים, עיגון וטכניקות NLP לשינוי דפוסים"}
        ],
        # Chapter 16
        16: [
            {"match_sec": "16.1", "filename": "פרק_16_image28.png", "title": "תרשים 16.1: תוכנית שבעת הימים לבריאות המעיים ומגוון צמחי"}
        ],
        # Chapter 17
        17: [
            {"match_sec": "17.1", "filename": "פרק_17_17.1למה_מעקב_אישי_עדיף_על_ניחוש_image30.png", "title": "תרשים 17.1: מודל ניטור אישי CEO Code ומדדי אנרגיה"},
            {"match_sec": "17.4", "filename": "פרק_17_image29.jpg", "title": "איור 17.4: סולם בריסטול הרפואי להערכת מרקם יציאות (סוגים 1-7)"},
            {"match_sec": "17.5", "filename": "פרק_17_17.5שבלונת_מעקב_מוכנה_לשימוש_image31.png", "title": "תרשים 17.5: שבלונת יומן מעקב 14 ימים לבריאות המעי"}
        ],
        # Chapter 18
        18: [
            {"match_sec": "18.1", "filename": "פרק_18_image32.jpg", "title": "תרשים 18.1: ניתוח מיתוסים, בדיקות מיקרוביום מסחריות ושיווק"}
        ],
        # Chapter 19
        19: [
            {"match_sec": "19.1", "filename": "פרק_19_image33.jpg", "title": "תרשים 19.1: חזון תוחלת הבריאות לאורך זמן"},
            {"match_sec": "19.2", "filename": "פרק_19_19.2פרוטוקול_התאוששות_ממעידה_image34.png", "title": "תרשים 19.2: פרוטוקול התאוששות ממעידה — שלב 1 ושלב 2"},
            {"match_sec": "19.4", "filename": "פרק_19_19.2פרוטוקול_התאוששות_ממעידה_image35.png", "title": "תרשים 19.4: מפת העוגנים של חיוניות יומיומית"}
        ]
    }

    # Medical Knowledge Categories
    categories = [
        {
            "id": "cat-all",
            "icon": "🌐",
            "name": "כל הנושאים",
            "subtopics": []
        },
        {
            "id": "cat-anatomy",
            "icon": "🧬",
            "name": "אנטומיה ומערכת העיכול",
            "subtopics": [
                {"name": "מסע המזון בפה ובאיברים", "target": "sec-1-1"},
                {"name": "הקיבה והחומציות", "target": "sec-1-2"},
                {"name": "המעי הדק והספיגה", "target": "sec-1-3"},
                {"name": "המעי הגס והתסיסה", "target": "sec-1-4"}
            ]
        },
        {
            "id": "cat-microbiome",
            "icon": "🦠",
            "name": "מיקרוביום ומחסום המעי",
            "subtopics": [
                {"name": "הקהילה המיקרוביאלית", "target": "sec-2-1"},
                {"name": "מחסום המעי ושומרי הסף", "target": "sec-2-2"},
                {"name": "חומצות שומן קצרות שרשרת & בוטיראט", "target": "sec-2-3"},
                {"name": "פרוביוטיקה ופרה־ביוטיקה", "target": "sec-2-4"},
                {"name": "מזונות מותססים", "target": "sec-2-5"},
                {"name": "התאוששות מאנטיביוטיקה", "target": "sec-3-5"}
            ]
        },
        {
            "id": "cat-nutrition",
            "icon": "🥗",
            "name": "תזונה, סיבים ורכיבים",
            "subtopics": [
                {"name": "פרה־ביוטיקה וסוגי סיבים", "target": "sec-3-1"},
                {"name": "התזונה הים־תיכונית הירוקה", "target": "sec-3-3"},
                {"name": "צלחת מאוזנת", "target": "sec-4-1"},
                {"name": "דגנים וקטניות", "target": "sec-4-2"},
                {"name": "תוויות מזון", "target": "sec-4-4"},
                {"name": "תזמון רכיבים וקפאין", "target": "sec-11-1"}
            ]
        },
        {
            "id": "cat-symptoms",
            "icon": "🩺",
            "name": "תסמינים, IBS ופרוטוקולים",
            "subtopics": [
                {"name": "נפיחות וגזים", "target": "sec-5-2"},
                {"name": "עצירות ופתרונות", "target": "sec-5-3"},
                {"name": "תסמונת המעי הרגיז (IBS)", "target": "sec-5-5"},
                {"name": "דיאטת FODMAP", "target": "sec-5-6"},
                {"name": "צליאק וגלוטן", "target": "sec-5-7"},
                {"name": "צרבת ורפלוקס", "target": "sec-5-8"}
            ]
        },
        {
            "id": "cat-gut-brain",
            "icon": "🧠",
            "name": "ציר המעי–מוח ואנרגיה",
            "subtopics": [
                {"name": "ציר המעי–מוח", "target": "sec-9-1"},
                {"name": "סרוטונין ונוירוטרנסמיטרים", "target": "sec-9-2"},
                {"name": "עייפות כרונית (ME/CFS)", "target": "sec-9-3"},
                {"name": "תנועתיות ו-Pacing", "target": "sec-13-5"}
            ]
        },
        {
            "id": "cat-chrono",
            "icon": "⏰",
            "name": "כרונו־תזונה ושינה",
            "subtopics": [
                {"name": "השעון הצירקדי", "target": "sec-10-1"},
                {"name": "כרונוטיפ ומלטונין", "target": "sec-10-2"},
                {"name": "אכילה מוגבלת בזמן (16:8 TRE)", "target": "sec-10-5"},
                {"name": "שינה, לחץ ו-CBT-I", "target": "sec-12-1"}
            ]
        },
        {
            "id": "cat-diagnosis",
            "icon": "📊",
            "name": "אבחון, בדיקות וניטור",
            "subtopics": [
                {"name": "בדיקות דם וצואה", "target": "sec-6-2"},
                {"name": "קלפרוטקטין ואנדוסקופיה", "target": "sec-6-3"},
                {"name": "סולם בריסטול", "target": "sec-17-4"},
                {"name": "יומן מעקב 14 ימים", "target": "sec-17-5"}
            ]
        },
        {
            "id": "cat-lifestyle",
            "icon": "💡",
            "name": "הרגלים ואורח חיים",
            "subtopics": [
                {"name": "הרגלים אטומיים ו-Tiny Habits", "target": "sec-14-2"},
                {"name": "NLP ויומן טריגרים", "target": "sec-15-4"},
                {"name": "תוכנית 7 הימים", "target": "sec-16-1"},
                {"name": "פרוטוקול התאוששות ממעידה", "target": "sec-19-2"}
            ]
        }
    ]

    # Process each chapter markdown content and inject images IN-LINE right below their exact matching text section!
    processed_chapters = {}
    for num in range(1, 20):
        ch_file = book_dir / f"chapter_{num:02d}.md"
        if not ch_file.exists():
            continue

        content = ch_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else f"פרק {num}"

        # Render structured HTML with in-line image cards directly under sections
        lines = content.split("\n")
        html_lines = []
        ch_imgs = image_mappings.get(num, [])

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check section headers like "2.1 ...", "2.2 ...", "17.4 ..."
            sec_match = re.match(r'^(\d+\.\d+)\s+(.+)$', line_str)
            if sec_match:
                sec_num = sec_match.group(1)
                sec_title = sec_match.group(2)
                sec_id = f"sec-{num}-{sec_num.split('.')[1]}"

                html_lines.append(f'<div class="section-block" id="{sec_id}">')
                html_lines.append(f'<h3 class="section-title"><span class="sec-num">{sec_num}</span> {process_inline_markup(sec_title)}</h3>')

                # Find image for this section if exists
                matching_img = next((img for img in ch_imgs if img["match_sec"] == sec_num), None)
                if matching_img:
                    url_path = f"/assets/gut_images/{urllib.parse.quote(matching_img['filename'])}"
                    html_lines.append(f'''
                    <div class="inline-figure-card">
                        <div class="figure-badge">📷 איור רפואי מקורר: {sec_num}</div>
                        <h4 class="figure-title">{matching_img["title"]}</h4>
                        <img src="{url_path}" class="figure-inline-img" alt="{matching_img["title"]}" onclick="openModal('{url_path}')">
                        <div class="figure-caption">לחץ על התמונה להגדלה באיכות מלאה (High-Res Modal)</div>
                    </div>''')

                continue

            if line_str.startswith("# "):
                html_lines.append(f'<h1 class="chapter-main-title">{process_inline_markup(line_str[2:])}</h1>')
            elif line_str.startswith("## "):
                html_lines.append(f'<h2 class="sub-chapter-title">{process_inline_markup(line_str[3:])}</h2>')
            elif line_str.startswith("### "):
                html_lines.append(f'<h3 class="section-title">{process_inline_markup(line_str[4:])}</h3>')
            elif line_str.startswith("---"):
                html_lines.append('<hr class="section-divider">')
            else:
                html_lines.append(f'<p class="article-paragraph">{process_inline_markup(line_str)}</p>')

        processed_chapters[num] = {
            "number": num,
            "title": title,
            "html": "\n".join(html_lines)
        }

    categories_json = json.dumps(categories, ensure_ascii=False)
    chapters_json = json.dumps(processed_chapters, ensure_ascii=False)

    html_page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>פורטל בריאות המעי, התזונה והמטבוליזם | Gut Health Portal</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #090d16;
            color: #f8fafc;
            min-height: 100vh;
        }}

        /* FIXED TOP NAVIGATION BAR - NO OVERFLOW/SCROLLBAR ISSUES */
        .navbar {{
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }}

        .nav-inner {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
        }}

        .brand-box {{
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            flex-shrink: 0;
        }}

        .brand-icon {{
            background: linear-gradient(135deg, #0284c7, #22c55e);
            color: #fff;
            font-size: 1.3rem;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 12px rgba(2, 132, 199, 0.4);
        }}

        .brand-text h1 {{
            margin: 0;
            font-size: 1.2rem;
            color: #38bdf8;
            font-weight: 800;
        }}

        .brand-text p {{
            margin: 0;
            font-size: 0.78rem;
            color: #94a3b8;
        }}

        .nav-categories-bar {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none; /* Hide scrollbar for clean UI */
            padding: 4px 0;
        }}
        .nav-categories-bar::-webkit-scrollbar {{ display: none; }}

        .cat-tab-btn {{
            background: #1e293b;
            color: #cbd5e1;
            border: 1px solid #334155;
            padding: 7px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .cat-tab-btn:hover, .cat-tab-btn.active {{
            background: #0284c7;
            color: #fff;
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(2, 132, 199, 0.4);
        }}

        .nav-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }}

        .nav-btn {{
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .nav-btn:hover {{
            background: #0284c7;
            color: #fff;
        }}

        /* HERO SECTION */
        .hero-banner {{
            background: radial-gradient(circle at top center, #1e293b 0%, #090d16 80%);
            padding: 2.5rem 1.5rem 2rem 1.5rem;
            text-align: center;
            border-bottom: 1px solid #1e293b;
        }}

        .hero-banner h2 {{
            font-size: 2.1rem;
            font-weight: 900;
            margin: 0 0 0.5rem 0;
            color: #f8fafc;
        }}

        .hero-banner h2 span {{
            background: linear-gradient(135deg, #38bdf8, #22c55e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .hero-banner p {{
            color: #94a3b8;
            font-size: 1.05rem;
            max-width: 700px;
            margin: 0 auto 1.5rem auto;
        }}

        /* SUB-TOPICS QUICK BAR (תתי נושאים קליקביליים) */
        .subtopics-bar {{
            max-width: 1200px;
            margin: 0 auto 1.5rem auto;
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }}

        .subtopics-title {{
            font-size: 0.9rem;
            font-weight: bold;
            color: #38bdf8;
            margin-bottom: 8px;
        }}

        .subtopic-pills-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .subtopic-pill {{
            background: #1e293b;
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 5px 12px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .subtopic-pill:hover {{
            background: #064e3b;
            color: #a7f3d0;
            border-color: #22c55e;
            box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
            transform: translateY(-1px);
        }}

        /* MAIN ARTICLE AREA - CLEAN 1-COLUMN MEDICAL APP LAYOUT */
        .main-container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}

        .article-card {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 2.5rem 3rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin-bottom: 2.5rem;
        }}

        .chapter-main-title {{
            color: #38bdf8;
            font-size: 1.85rem;
            font-weight: 800;
            margin-top: 0;
            border-bottom: 2px solid #1e293b;
            padding-bottom: 0.75rem;
            margin-bottom: 1.5rem;
        }}

        .sub-chapter-title {{
            color: #7dd3fc;
            font-size: 1.45rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}

        .section-block {{
            margin: 2rem 0;
            padding: 1rem 1.25rem;
            border-radius: 10px;
            transition: all 0.3s ease;
        }}

        .section-block.highlighted {{
            background: rgba(56, 189, 248, 0.08);
            border: 2px solid #38bdf8;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
        }}

        .section-title {{
            color: #a7f3d0;
            font-size: 1.25rem;
            margin-top: 0;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .sec-num {{
            background: #1e293b;
            color: #38bdf8;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: bold;
        }}

        .article-paragraph {{
            line-height: 1.85;
            font-size: 1.08rem;
            color: #e2e8f0;
            margin-bottom: 1.2rem;
        }}

        .block-anchor-tag {{
            font-size: 0.75rem;
            color: #64748b;
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 6px;
            font-family: monospace;
            display: inline-block;
        }}

        /* INLINE IMAGE CARD EMBEDDED DIRECTLY INSIDE ARTICLE FLOW */
        .inline-figure-card {{
            background: #090d16;
            border: 2px solid #0284c7;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1.5rem 0 2rem 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.6);
        }}

        .figure-badge {{
            display: inline-block;
            background: rgba(2, 132, 199, 0.2);
            color: #38bdf8;
            border: 1px solid rgba(2, 132, 199, 0.4);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .figure-title {{
            color: #f8fafc;
            font-size: 1.1rem;
            font-weight: bold;
            margin: 0 0 1rem 0;
        }}

        .figure-inline-img {{
            width: 100%;
            max-height: 500px;
            object-fit: contain;
            background: #000;
            border-radius: 8px;
            border: 1px solid #334155;
            cursor: pointer;
            transition: transform 0.2s ease;
        }}

        .figure-inline-img:hover {{
            transform: scale(1.01);
            border-color: #38bdf8;
        }}

        .figure-caption {{
            color: #94a3b8;
            font-size: 0.85rem;
            margin-top: 8px;
            text-align: center;
        }}

        /* FULLSCREEN MODAL VIEWER */
        .modal-fullscreen {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.92);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 2rem;
        }}

        .modal-fullscreen.active {{
            display: flex;
        }}

        .modal-fullscreen-img {{
            max-width: 92vw;
            max-height: 88vh;
            border-radius: 10px;
            border: 2px solid #38bdf8;
            box-shadow: 0 0 40px rgba(56, 189, 248, 0.6);
        }}
    </style>
</head>
<body>
    <!-- FIXED TOP NAVBAR -->
    <nav class="navbar">
        <div class="nav-inner">
            <a href="#" class="brand-box" onclick="showCategory('cat-all')">
                <div class="brand-icon">🔬</div>
                <div class="brand-text">
                    <h1>פורטל בריאות המעי והמטבוליזם</h1>
                    <p>Gut Health & Microbiome Hub</p>
                </div>
            </a>
            <div class="nav-categories-bar" id="navCategoriesBar">
                <!-- Category Tabs Load Here -->
            </div>
            <div class="nav-actions">
                <a href="/" class="nav-btn">🔍 חיפוש היברידי (RAG)</a>
                <a href="/data/books/inner_gate_clean.docx" download class="nav-btn" style="background:#0284c7; color:#fff; border:none;">📥 DOCX</a>
            </div>
        </div>
    </nav>

    <!-- HERO BANNER -->
    <header class="hero-banner">
        <h2>פורטל הידע המדעי והקליני <span>לבריאות המעיים והאנרגיה</span></h2>
        <p>מאגר ידע נושאי מקיף המלווה ב-35 איורים רפואיים מקוריים המשובצים ישירות בתוך הטקסט בהקשרם הקליני.</p>

        <!-- SUB-TOPICS QUICK ACCESS BAR (תתי נושאים נלחצים) -->
        <div class="subtopics-bar">
            <div class="subtopics-title">⚡ ניווט מהיר לתתי-נושאים קליניים (לחץ למעבר ישיר והדגשת האיור):</div>
            <div class="subtopic-pills-list" id="subtopicPillsList">
                <!-- Subtopic pills load dynamically -->
            </div>
        </div>
    </header>

    <!-- MAIN ARTICLE AREA -->
    <main class="main-container" id="mainContainer">
        <!-- Articles Render Here -->
    </main>

    <!-- FULLSCREEN MODAL -->
    <div class="modal-fullscreen" id="fullscreenModal" onclick="closeModal()">
        <img src="" id="modalImgElement" class="modal-fullscreen-img" alt="Enlarged Medical Diagram">
    </div>

    <script>
        const categoriesData = {categories_json};
        const chaptersData = {chapters_json};

        function initApp() {{
            renderCategoriesBar();
            renderSubtopicsBar();
            showCategory('cat-all');
        }}

        function renderCategoriesBar() {{
            const bar = document.getElementById('navCategoriesBar');
            let html = '';
            categoriesData.forEach(cat => {{
                html += `<button class="cat-tab-btn" id="btn-${{cat.id}}" onclick="showCategory('${{cat.id}}')">${{cat.icon}} ${{cat.name}}</button>`;
            }});
            bar.innerHTML = html;
        }}

        function renderSubtopicsBar() {{
            const list = document.getElementById('subtopicPillsList');
            let html = '';
            categoriesData.forEach(cat => {{
                if (cat.subtopics) {{
                    cat.subtopics.forEach(sub => {{
                        html += `<span class="subtopic-pill" onclick="navigateToSection('${{sub.target}}', '${{cat.id}}')">${{cat.icon}} ${{sub.name}}</span>`;
                    }});
                }}
            }});
            list.innerHTML = html;
        }}

        function showCategory(catId) {{
            // Active tab styling
            document.querySelectorAll('.cat-tab-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById('btn-' + catId);
            if (activeBtn) activeBtn.classList.add('active');

            const container = document.getElementById('mainContainer');
            let html = '';

            let targetChapters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
            if (catId !== 'cat-all') {{
                const cat = categoriesData.find(c => c.id === catId);
                if (cat) {{
                    if (catId === 'cat-anatomy') targetChapters = [1];
                    else if (catId === 'cat-microbiome') targetChapters = [2, 3];
                    else if (catId === 'cat-nutrition') targetChapters = [4, 11];
                    else if (catId === 'cat-symptoms') targetChapters = [5, 7];
                    else if (catId === 'cat-gut-brain') targetChapters = [9, 13];
                    else if (catId === 'cat-chrono') targetChapters = [10, 12];
                    else if (catId === 'cat-diagnosis') targetChapters = [6, 17, 18];
                    else if (catId === 'cat-lifestyle') targetChapters = [8, 14, 15, 16, 19];
                }}
            }}

            targetChapters.forEach(chNum => {{
                const ch = chaptersData[chNum];
                if (ch) {{
                    html += `<article class="article-card" id="chapter-card-${{chNum}}">${{ch.html}}</article>`;
                }}
            }});

            container.innerHTML = html;
            window.scrollTo({{ top: 380, behavior: 'smooth' }});
        }}

        function navigateToSection(targetSecId, catId) {{
            // First show category if not all shown
            showCategory(catId || 'cat-all');

            setTimeout(() => {{
                const el = document.getElementById(targetSecId);
                if (el) {{
                    // Remove previous highlights
                    document.querySelectorAll('.section-block').forEach(s => s.classList.remove('highlighted'));
                    
                    // Highlight target section
                    el.classList.add('highlighted');
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }}, 150);
        }}

        function openModal(imgUrl) {{
            document.getElementById('modalImgElement').src = imgUrl;
            document.getElementById('fullscreenModal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('fullscreenModal').classList.remove('active');
        }}

        document.addEventListener('DOMContentLoaded', initApp);
    </script>
</body>
</html>"""

    output_file = site_dir / "index.html"
    output_file.write_text(html_page, encoding="utf-8")
    print(f"SUCCESS! Built Perfect Medical Web Site at {output_file}. File size: {len(html_page)}")


def process_inline_markup(text: str) -> str:
    # Convert [[Wikilinks]] to clickable badges
    text = re.sub(r'\[\[([^\]]+)\]\]', r'<span class="subtopic-pill" style="font-size:0.8rem; margin:0 2px;">🔗 \1</span>', text)
    # Highlight ^block-anchor tags
    text = re.sub(r'\^([a-zA-Z0-9_\-]+)', r'<span class="block-anchor-tag">^\1</span>', text)
    return text


if __name__ == "__main__":
    generate_perfect_website()
