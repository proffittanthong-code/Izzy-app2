from flask import Flask, request, jsonify, render_template_string
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ImageDrop</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0a0a0a; --border: #222;
      --accent: #e8c97e; --text: #f0ece4; --muted: #666;
      --error: #e07070; --success: #7ec4a0;
    }
    body { background: var(--bg); color: var(--text); font-family: 'DM Mono', monospace; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 60px 20px; }
    header { text-align: center; margin-bottom: 50px; }
    .eyebrow { font-size: 11px; letter-spacing: 0.3em; color: var(--accent); text-transform: uppercase; margin-bottom: 12px; }
    h1 { font-family: 'Playfair Display', serif; font-size: clamp(2.8rem, 7vw, 5rem); font-weight: 900; line-height: 1; }
    h1 span { color: var(--accent); }
    .sub { margin-top: 14px; color: var(--muted); font-size: 11px; letter-spacing: 0.08em; }
    .drop-zone { width: 100%; max-width: 600px; border: 1.5px dashed var(--border); border-radius: 4px; padding: 60px 40px; text-align: center; cursor: pointer; position: relative; transition: border-color 0.2s, background 0.2s; }
    .drop-zone:hover, .drop-zone.over { border-color: var(--accent); background: rgba(232,201,126,0.04); }
    .drop-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%; }
    .dz-icon { font-size: 44px; margin-bottom: 16px; display: block; opacity: 0.5; }
    .drop-zone h2 { font-family: 'Playfair Display', serif; font-size: 1.3rem; margin-bottom: 8px; }
    .drop-zone p { font-size: 11px; color: var(--muted); }
    .progress-bar { width: 100%; max-width: 600px; height: 2px; background: var(--border); margin-top: 14px; border-radius: 1px; overflow: hidden; display: none; }
    .progress-fill { height: 100%; background: var(--accent); width: 0%; transition: width 0.3s; }
    .status { margin-top: 12px; font-size: 11px; color: var(--muted); max-width: 600px; width: 100%; min-height: 18px; }
    .status.ok { color: var(--success); }
    .status.err { color: var(--error); }
    .gallery { margin-top: 50px; width: 100%; max-width: 960px; }
    .gallery-top { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 24px; }
    .gallery-top h3 { font-family: 'Playfair Display', serif; font-size: 1.1rem; }
    .gallery-top span { font-size: 11px; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
    .grid-item { aspect-ratio: 1; overflow: hidden; border-radius: 3px; border: 1px solid var(--border); transition: transform 0.2s, border-color 0.2s; background: #111; }
    .grid-item:hover { transform: scale(1.02); border-color: var(--accent); }
    .grid-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .empty { text-align: center; padding: 40px; color: var(--muted); font-size: 11px; border: 1px solid var(--border); border-radius: 3px; letter-spacing: 0.1em; }
    .spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; margin-right: 6px; vertical-align: middle; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .debug { margin-top: 8px; font-size: 10px; color: var(--muted); max-width: 600px; width: 100%; word-break: break-all; }
  </style>
</head>
<body>
<header>
  <p class="eyebrow">Upload Studio</p>
  <h1>Image<span>Drop</span></h1>
  <p class="sub">Drag &amp; drop or click to upload &mdash; PNG, JPG, GIF, WEBP up to 16MB</p>
</header>
<div class="drop-zone" id="dropZone">
  <input type="file" id="fileInput" accept="image/*" multiple/>
  <span class="dz-icon">⬡</span>
  <h2>Drop images here</h2>
  <p>or click to browse files</p>
</div>
<div class="progress-bar" id="progressBar"><div class="progress-fill" id="progressFill"></div></div>
<div class="status" id="statusEl">Ready.</div>
<div class="debug" id="debugEl"></div>
<div class="gallery">
  <div class="gallery-top">
    <h3>Uploaded Images</h3>
    <span id="countEl">0 images</span>
  </div>
  <div class="grid" id="grid">
    <div class="empty" id="emptyEl">No images yet.</div>
  </div>
</div>
<script>
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const statusEl = document.getElementById('statusEl');
  const debugEl = document.getElementById('debugEl');
  const grid = document.getElementById('grid');
  const countEl = document.getElementById('countEl');
  const progressBar = document.getElementById('progressBar');
  const progressFill = document.getElementById('progressFill');
  let count = 0;

  async function loadImages() {
    try {
      const res = await fetch('/images');
      const images = await res.json();
      images.forEach(img => addImage(img.url, img.original, false));
    } catch(e) {
      debugEl.textContent = 'Load error: ' + e.message;
    }
  }

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
  dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('over'); handleFiles(e.dataTransfer.files); });
  fileInput.addEventListener('change', () => handleFiles(fileInput.files));

  function setStatus(msg, cls) { statusEl.textContent = msg; statusEl.className = 'status ' + (cls||''); }

  async function handleFiles(files) {
    if (!files.length) return;
    const arr = Array.from(files);
    progressBar.style.display = 'block';
    progressFill.style.width = '0%';
    setStatus('Uploading...');
    let done = 0;
    for (const f of arr) {
      await uploadOne(f);
      done++;
      progressFill.style.width = (done / arr.length * 100) + '%';
    }
    setTimeout(() => progressBar.style.display = 'none', 800);
    setStatus('✓ ' + done + ' image(s) uploaded!', 'ok');
    fileInput.value = '';
  }

  async function uploadOne(file) {
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/upload', { method: 'POST', body: form });
      const data = await res.json();
      debugEl.textContent = 'Last response: ' + JSON.stringify(data);
      if (data.success && data.url) {
        addImage(data.url, file.name, true);
      } else {
        setStatus('Error: ' + (data.error || 'Unknown error'), 'err');
      }
    } catch(e) {
      setStatus('Upload failed: ' + e.message, 'err');
      debugEl.textContent = 'Fetch error: ' + e.message;
    }
  }

  function addImage(url, name, prepend) {
    const empty = document.getElementById('emptyEl');
    if (empty) empty.remove();
    count++;
    countEl.textContent = count + ' image' + (count !== 1 ? 's' : '');
    const div = document.createElement('div');
    div.className = 'grid-item';
    const img = document.createElement('img');
    img.alt = name;
    img.loading = 'lazy';
    img.onerror = function() {
      debugEl.textContent = 'Image failed to load from URL: ' + url;
      div.style.border = '1px solid var(--error)';
    };
    img.onload = function() {
      debugEl.textContent = 'Image loaded OK from: ' + url;
    };
    img.src = url;
    div.appendChild(img);
    if (prepend) grid.prepend(div);
    else grid.appendChild(div);
  }

  loadImages();
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/images')
def get_images():
    try:
        result = cloudinary.api.resources(type='upload', max_results=100, resource_type='image')
        images = [{'url': r['secure_url'], 'original': r['public_id']} for r in result.get('resources', [])]
        return jsonify(images)
    except Exception as e:
        return jsonify([])

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
    try:
        result = cloudinary.uploader.upload(file, resource_type='image')
        url = result.get('secure_url', '')
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
