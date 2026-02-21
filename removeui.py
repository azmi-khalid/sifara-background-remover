import os
import torch
import io
import base64
from flask import Flask, request, render_template_string, jsonify
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

app = Flask(__name__)

# 1. Konfigurasi Device & Model
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model_name = "ZhengPeng7/BiRefNet"

print(f"🚀 Status: Menggunakan {device}")
model = AutoModelForImageSegmentation.from_pretrained(model_name, trust_remote_code=True, torch_dtype=torch.float32)
model.to(device)
model.float()
model.eval()

# 2. UI MODERN & ELEGAN (Internal CSS & JS)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sifara Tech AI | Professional BG Remover</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">

    <style>
        :root {
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --dark-bg: #0f172a;
            --card-bg: rgba(255, 255, 255, 0.95);
            --text-main: #1e293b;
            --text-muted: #64748b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--dark-bg);
            background-image: radial-gradient(circle at 2px 2px, #1e293b 1px, transparent 0);
            background-size: 40px 40px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: var(--text-main);
        }

        .main-container {
            width: 90%;
            max-width: 1000px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            background: var(--card-bg);
            padding: 3rem;
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        }

        @media (max-width: 850px) {
            .main-container { grid-template-columns: 1fr; padding: 1.5rem; }
        }

        .brand-section { border-right: 1px solid #e2e8f0; padding-right: 2rem; }
        @media (max-width: 850px) { .brand-section { border-right: none; padding-right: 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 2rem; } }

        .logo { font-size: 1.5rem; font-weight: 700; color: var(--primary); margin-bottom: 1rem; display: flex; align-items: center; gap: 8px; }
        h1 { font-size: 2.2rem; font-weight: 800; line-height: 1.2; margin-bottom: 1rem; color: #0f172a; }
        p.subtitle { color: var(--text-muted); line-height: 1.6; margin-bottom: 2rem; }

        .upload-zone {
            position: relative;
            border: 2px dashed #cbd5e1;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
            background: #f8fafc;
            cursor: pointer;
        }
        .upload-zone:hover { border-color: var(--primary); background: #eff6ff; }

        input[type="file"] { position: absolute; width: 100%; height: 100%; top: 0; left: 0; opacity: 0; cursor: pointer; }

        .btn-primary {
            background: var(--primary);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 12px;
            font-weight: 600;
            width: 100%;
            margin-top: 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1rem;
        }
        .btn-primary:hover { background: var(--primary-hover); transform: translateY(-2px); }
        .btn-primary:disabled { background: #94a3b8; transform: none; }

        /* PREVIEW AREA */
        .preview-section { display: flex; flex-direction: column; justify-content: center; align-items: center; background: #f1f5f9; border-radius: 16px; min-height: 300px; position: relative; overflow: hidden; }

        .checkerboard {
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            background-image: linear-gradient(45deg, #e2e8f0 25%, transparent 25%), linear-gradient(-45deg, #e2e8f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #e2e8f0 75%), linear-gradient(-45deg, transparent 75%, #e2e8f0 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
        }

        #result-img { max-width: 90%; max-height: 400px; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.2)); border-radius: 8px; display: none; }

        .placeholder-text { color: #94a3b8; font-weight: 500; text-align: center; }

        #loader { display: none; text-align: center; }
        .spinner { border: 4px solid rgba(0,0,0,0.1); width: 36px; height: 36px; border-radius: 50%; border-left-color: var(--primary); animation: spin 1s linear infinite; margin: 0 auto 1rem; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        .download-btn {
            background: #10b981;
            color: white;
            text-decoration: none;
            padding: 0.8rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            margin-top: 1.5rem;
            display: none;
            transition: background 0.3s;
        }
        .download-btn:hover { background: #059669; }
    </style>
</head>
<body>

<div class="main-container">
    <div class="brand-section">
        <div class="logo">🚀 Sifara Tech AI</div>
        <h1>Hapus Background Sekelas Profesional.</h1>
        <p class="subtitle">Pastikan warna objek dan latar belakang terlihat kontras agar AI dapat mendeteksi setiap lekukan dengan sempurna.</p>

        <form id="uploadForm">
            <div class="upload-zone" id="dropZone">
                <p id="file-name">Pilih foto atau tarik ke sini</p>
                <input type="file" id="fileInput" accept="image/*" required>
            </div>
            <button type="submit" id="processBtn" class="btn-primary">Hapus Background</button>
        </form>
    </div>

    <div class="preview-section">
        <div id="loader">
            <div class="spinner"></div>
            <p style="font-weight: 600; color: var(--primary);">Menghitung di GPU M3...</p>
        </div>

        <div id="placeholder" class="placeholder-text">
            Hasil preview akan muncul di sini
        </div>

        <div class="checkerboard" id="result-container" style="display: none;">
            <img id="result-img" src="" alt="Hasil AI">
        </div>

        <a id="downloadLink" class="download-btn" download="sifara_transparent.png">Download PNG Transparan</a>
    </div>
</div>

<script>
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('file-name');
    const loader = document.getElementById('loader');
    const placeholder = document.getElementById('placeholder');
    const resultContainer = document.getElementById('result-container');
    const resultImg = document.getElementById('result-img');
    const downloadLink = document.getElementById('downloadLink');
    const processBtn = document.getElementById('processBtn');

    // Menambahkan tombol Refresh secara dinamis
    const resetBtn = document.createElement('button');
    resetBtn.innerText = "🔄 Olah Foto Lain";
    resetBtn.className = "btn-primary";
    resetBtn.style.display = "none";
    resetBtn.style.background = "#64748b"; // Warna abu-abu agar beda dengan tombol utama
    document.querySelector('.brand-section').appendChild(resetBtn);

    fileInput.onchange = () => {
        if(fileInput.files.length > 0) fileName.innerText = "File: " + fileInput.files[0].name;
    };

    // Fungsi untuk mereset tampilan
    resetBtn.onclick = () => {
        form.reset();
        fileName.innerText = "Pilih foto atau tarik ke sini";
        placeholder.style.display = "block";
        resultContainer.style.display = "none";
        downloadLink.style.display = "none";
        resetBtn.style.display = "none";
        form.style.display = "block";
        processBtn.disabled = false;
        processBtn.innerText = "Mulai Proses AI";
    };

    form.onsubmit = async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0) return;

        loader.style.display = "block";
        placeholder.style.display = "none";
        resultContainer.style.display = "none";
        processBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const response = await fetch('/process', { method: 'POST', body: formData });
            const data = await response.json();

            if (data.success) {
                resultImg.src = "data:image/png;base64," + data.image;
                downloadLink.href = "data:image/png;base64," + data.image;
                
                loader.style.display = "none";
                resultContainer.style.display = "flex";
                resultImg.style.display = "block";
                downloadLink.style.display = "inline-block";
                
                // Sembunyikan form upload dan tampilkan tombol reset
                form.style.display = "none";
                resetBtn.style.display = "block";
            }
        } catch (error) {
            alert("Terjadi kesalahan teknis.");
            loader.style.display = "none";
            processBtn.disabled = false;
        }
    };
</script>

</body>
</html>
"""


# 3. Backend Logic (Tetap sama seperti permintaan sebelumnya)
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/process', methods=['POST'])
def process():
    file = request.files.get('file')
    if not file: return jsonify({"success": False})

    img = Image.open(file.stream).convert("RGB")
    w, h = img.size
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    input_tensor = transform(img).unsqueeze(0).to(device).to(torch.float32)

    with torch.no_grad():
        output = model(input_tensor)
        preds = output[-1].sigmoid().cpu()

    mask = transforms.ToPILImage()(preds[0].squeeze()).resize((w, h))
    img.putalpha(mask)

    # Encode ke Base64 untuk preview
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_str = base64.b64encode(img_io.getvalue()).decode('utf-8')

    # Auto-Save di MacBook
    save_path = os.path.expanduser("~/Downloads/Sifara_Results")
    if not os.path.exists(save_path): os.makedirs(save_path)
    file_save_name = os.path.join(save_path, f"bg_removed_{file.filename.split('.')[0]}.png")
    img.save(file_save_name)

    return jsonify({"success": True, "image": img_str})


if __name__ == '__main__':
    app.run(debug=False, port=5001, host='0.0.0.0')