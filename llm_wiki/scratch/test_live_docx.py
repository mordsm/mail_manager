from fastapi.testclient import TestClient
from app.api.main import app
import zipfile, io

client = TestClient(app)

buf = io.BytesIO()
content_xml = '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>פרומפטים והנחיות לכתיבת חוברת גינון הידרופוני</w:t></w:r></w:p></w:body></w:document>'

with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('word/document.xml', content_xml)

buf.seek(0)
files = {'file': ('פרומפט לספר.docx', buf.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
data = {'domain': 'Auto classify'}

resp = client.post('/api/v1/ingest/file', files=files, data=data)
print('Status Code:', resp.status_code)
print('JSON keys:', resp.json().keys())
print('JSON data:', resp.json())
