import os
import requests
import pandas as pd
import io
import logging
from flask import Flask, render_template_string, request, Response
from PyPDF2 import PdfReader
import ollama

# Konfigurasi
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
chat_history = []


# --- SETUP OFFLINE ASSETS ---
def setup_offline_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, 'static')
    files = {
        'tailwind.js': 'https://cdn.tailwindcss.com',
        'marked.min.js': 'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
        'highlight.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js',
        'tokyo-night.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/tokyo-night-dark.min.css'
    }
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    for filename, url in files.items():
        file_path = os.path.join(static_dir, filename)
        if not os.path.exists(file_path):
            try:
                response = requests.get(url)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                print(f"Error download {filename}: {e}")


setup_offline_files()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Sifara AI | Multimodal</title>
    <script src="/static/tailwind.js"></script>
    <script src="/static/marked.min.js"></script>
    <script src="/static/highlight.min.js"></script>
    <link rel="stylesheet" href="/static/tokyo-night.min.css">
    <style>
        body { background: #0b0e14; color: #cdd6f4; font-family: -apple-system, sans-serif; }
        .prose-content p { margin-bottom: 1rem; line-height: 1.7; color: #cbd5e1; }
        .code-container { position: relative; margin: 1.5rem 0; border: 1px solid #2f3b54; border-radius: 8px; overflow: hidden; }
        .code-header { background: #1f2937; color: #9ca3af; font-size: 11px; padding: 8px 16px; display: flex; justify-content: space-between; border-bottom: 1px solid #374151; font-family: monospace; }
        .code-block { background: #111827 !important; padding: 1rem; font-family: monospace; font-size: 13px; overflow-x: auto; }
        .copy-btn { background: #374151; color: #e5e7eb; border-radius: 4px; padding: 2px 8px; font-size: 10px; cursor: pointer; border: 1px solid #4b5563; }
        .ai-bubble { background: #131720; border: 1px solid #1f2937; }
        .user-bubble { background: #1d4ed8; border: 1px solid #1e40af; color: white; }
        @keyframes shimmer { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
        .animate-shimmer { animation: shimmer 5s infinite linear; }
    </style>
</head>
<body class="h-screen flex flex-col">
    <div class="flex-1 max-w-5xl w-full mx-auto flex flex-col p-4 md:p-8 overflow-hidden">
        <header class="mb-6 flex justify-between items-center border-b border-slate-800 pb-4">
            <div>
                <h1 class="flex items-baseline gap-2 text-4xl font-black tracking-tight uppercase">
                    <span class="bg-gradient-to-r from-white via-slate-200 to-white bg-[length:200%_auto] bg-clip-text text-transparent animate-shimmer">Sifara</span>
                    <span class="text-blue-500 drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]">AI</span>
                </h1>
                <span class="text-[10px] text-green-500 font-mono border border-green-900 bg-green-900/20 px-2 py-0.5 rounded animate-pulse uppercase tracking-widest">OFFLINE MODE</span>
            </div>
            <button onclick="clearChat()" class="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-md hover:bg-red-500/20 transition-all">RESET SESSION</button>
        </header>

        <div id="chat-box" class="flex-1 overflow-y-auto space-y-6 mb-4 pr-2 scroll-smooth">
            <div class="ai-bubble p-5 rounded-2xl max-w-[90%] shadow-lg text-sm">Asisten SIFARA siap menganalisis teks, PDF, atau Excel Anda.</div>
        </div>

        <div class="relative group">
            <div class="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>

            <input type="file" id="file-input" class="hidden" accept=".pdf,.csv,.xlsx" onchange="handleFileUpload()">

            <div class="relative flex items-end bg-[#0d1117] border border-slate-800 rounded-2xl p-2">
                <button onclick="document.getElementById('file-input').click()" class="p-3 mb-1 text-slate-400 hover:text-blue-400 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                </button>
                <textarea id="user-input" class="w-full bg-transparent p-3 pr-16 focus:outline-none text-slate-200 text-sm resize-none" rows="3" placeholder="Ketik pesan atau upload file..."></textarea>
                <button onclick="send()" class="absolute right-3 bottom-3 bg-gradient-to-r from-blue-600 to-indigo-600 p-3 rounded-xl text-white transform hover:scale-105 active:scale-95 shadow-lg">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                </button>
            </div>
            <div id="file-status" class="text-[10px] text-blue-400 mt-2 ml-4 font-mono hidden uppercase tracking-widest"></div>
        </div>
    </div>

    <script>
        document.getElementById('user-input').addEventListener('keydown', e => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

        async function handleFileUpload() {
            const fileInput = document.getElementById('file-input');
            const status = document.getElementById('file-status');
            const box = document.getElementById('chat-box');
            if (!fileInput.files[0]) return;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            status.innerText = "⏳ ANALYZING " + fileInput.files[0].name.toUpperCase() + "...";
            status.classList.remove('hidden');

            const res = await fetch('/upload', { method: 'POST', body: formData });
            const result = await res.json();
            if (res.ok) {
                status.innerText = "✅ " + fileInput.files[0].name.toUpperCase() + " LOADED";
                box.innerHTML += `<div class="ai-bubble p-4 rounded-xl text-[10px] italic text-blue-400 border-dashed border-blue-900">Dokumen berhasil dibaca. Sifara kini memiliki konteks file tersebut.</div>`;
            }
        }

        async function send() {
            const input = document.getElementById('user-input');
            const box = document.getElementById('chat-box');
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            box.innerHTML += `<div class="user-bubble p-5 rounded-2xl ml-auto max-w-[85%] text-sm shadow-md">${text}</div>`;
            box.scrollTop = box.scrollHeight;
            const aiDiv = document.createElement('div');
            aiDiv.className = 'ai-bubble p-5 rounded-2xl max-w-[90%] shadow-lg text-sm';
            aiDiv.innerHTML = '<p class="animate-pulse text-slate-500 font-mono text-xs">SIFARA IS THINKING...</p>';
            box.appendChild(aiDiv);

            const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: text }) });
            const reader = response.body.getReader();
            let fullText = '';
            while(true) {
                const {done, value} = await reader.read();
                if (done) break;
                fullText += new TextDecoder().decode(value);
                let html = marked.parse(fullText);
                html = html.replace(/<pre><code class="language-(.*?)">([\s\S]*?)<\/code><\/pre>/g, (m, lang, code) => {
                    const b64 = btoa(unescape(encodeURIComponent(code)));
                    return `<div class="code-container"><div class="code-header"><span>${lang.toUpperCase()}</span><button class="copy-btn" onclick="copyCode(this, '${b64}')">COPY</button></div><div class="code-block"><pre><code class="language-${lang}">${code}</code></pre></div></div>`;
                });
                aiDiv.innerHTML = `<div class="prose-content text-sm">${html}</div>`;
                box.scrollTop = box.scrollHeight;
                hljs.highlightAll();
            }
        }

        async function copyCode(btn, b64) {
            const txt = document.createElement("textarea");
            txt.innerHTML = atob(b64);
            await navigator.clipboard.writeText(txt.value);
            btn.innerText = 'COPIED';
            setTimeout(() => { btn.innerText = 'COPY'; }, 2000);
        }

        async function clearChat() { await fetch('/clear', {method: 'POST'}); location.reload(); }
    </script>
</body>
</html>
"""


@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)


@app.route('/clear', methods=['POST'])
def clear():
    global chat_history
    chat_history = []
    return "OK"


@app.route('/upload', methods=['POST'])
def upload():
    global chat_history
    file = request.files['file']
    ext = file.filename.split('.')[-1].lower()
    content = ""
    try:
        if ext == 'pdf':
            reader = PdfReader(file)
            for page in reader.pages: content += page.extract_text()
        elif ext == 'csv':
            content = pd.read_csv(file).to_string()
        elif ext == 'xlsx':
            content = pd.read_excel(file).to_string()

        # Masukkan ke history sebagai instruksi sistem agar AI paham konteks dokumen
        chat_history.append({'role': 'system', 'content': f"Konteks file {file.filename}: {content[:8000]}"})
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.route('/chat', methods=['POST'])
def chat():
    global chat_history
    prompt = request.json.get('prompt')
    chat_history.append({'role': 'user', 'content': prompt})
    if len(chat_history) > 10: chat_history = chat_history[-10:]  # Limit history sedikit lebih banyak karena ada file

    def stream():
        full_response = ""
        try:
            s = ollama.chat(model='qwen2.5-coder:3b', messages=chat_history, stream=True)
            for chunk in s:
                content = chunk['message']['content']
                full_response += content
                yield content
            chat_history.append({'role': 'assistant', 'content': full_response})
        except Exception as e:
            yield f"Error: {str(e)}"

    return Response(stream(), mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)