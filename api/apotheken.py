
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_text(self):
        return '\n'.join(self.text)

def fetch_apotheken(bezirk_code):
    """Eczane verilerini çek"""
    
    base_url = "https://notdienst.akberlin.de/notdienst/notdienstdisplay.html"
    params = {
        'tx_akbnotdienst_apothekendisplay[code]': bezirk_code,
        'tx_akbnotdienst_apothekendisplay[limit]': '3',
        'tx_akbnotdienst_apothekendisplay[action]': 'display',
        'tx_akbnotdienst_apothekendisplay[controller]': 'Notdienst'
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # HTML'i parse et
        parser = SimpleHTMLParser()
        parser.feed(html)
        text = parser.get_text()
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Filtrele
        skip_keywords = [
            'Apothekerkammer Berlin',
            'Notdienstdisplay',
            'Apothekennotdienst',
            'Uhr bis',
            'function',
            'window',
            'Copyright'
        ]
        
        filtered_lines = []
        for line in lines:
            if len(line) < 3:
                continue
            if any(kw in line for kw in skip_keywords):
                continue
            if re.match(r'\d{2}\.\d{2}\.\d{4}', line):
                continue
            if any(c in line for c in ['{', '}', '(', ')']):
                continue
            filtered_lines.append(line)
        
        # Eczaneleri parse et
        apotheken = []
        i = 0
        
        while i < len(filtered_lines) and len(apotheken) < 3:
            line = filtered_lines[i]
            
            if 'Apotheke' in line and len(line.split()) <= 5:
                name = line
                address = ''
                phone = ''
                
                if i + 1 < len(filtered_lines):
                    next_line = filtered_lines[i + 1]
                    if ('str.' in next_line.lower() or any(c.isdigit() for c in next_line)) and 'Apotheke' not in next_line:
                        address = next_line
                        i += 1
                        
                        if i + 1 < len(filtered_lines):
                            plz_line = filtered_lines[i + 1]
                            if re.match(r'\d{5}.*Berlin', plz_line):
                                address += ' ' + plz_line
                                i += 1
                
                if i + 1 < len(filtered_lines):
                    next_line = filtered_lines[i + 1]
                    if 'Telefon' in next_line or 'Tel' in next_line:
                        phone = next_line
                        i += 1
                    elif next_line.isdigit() and len(next_line) >= 6:
                        phone = 'Telefon: ' + next_line
                        i += 1
                
                if name and address and phone:
                    apotheken.append({
                        'name': name,
                        'address': address,
                        'phone': phone
                    })
            
            i += 1
        
        return apotheken
    
    except Exception as e:
        print(f"Error: {e}")
        return []

class handler(BaseHTTPRequestHandler):
    """Vercel Handler"""
    
    def do_GET(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        # Query parametrelerini al
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        bezirk_code = params.get('code', ['0950'])[0]
        
        # Veriyi çek
        apotheken = fetch_apotheken(bezirk_code)
        
        # JSON olarak döndür
        response = {
            'success': True,
            'code': bezirk_code,
            'apotheken': apotheken,
            'count': len(apotheken)
        }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        return
