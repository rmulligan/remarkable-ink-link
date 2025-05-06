// Minimal InkLink Web UI Logic

let fileId = null;
let responseId = null;

// Helper: Show/hide sections
function showSection(id) {
  document.getElementById('auth-section').style.display = 'none';
  document.getElementById('upload-section').style.display = 'none';
  document.getElementById('process-section').style.display = 'none';
  document.getElementById('response-section').style.display = 'none';
  document.getElementById(id).style.display = '';
}

// Helper: Show error
function showError(msg) {
  document.getElementById('error').textContent = msg || '';
}

// Authenticate reMarkable
document.getElementById('remarkable-auth-form').onsubmit = async (e) => {
  e.preventDefault();
  showError('');
  const token = document.getElementById('remarkable-token').value;
  const res = await fetch('/auth/remarkable', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token })
  });
  if (res.ok) {
    showSection('upload-section');
  } else {
    showError('reMarkable authentication failed');
  }
};

// Authenticate MyScript
document.getElementById('myscript-auth-form').onsubmit = async (e) => {
  e.preventDefault();
  showError('');
  const application_key = document.getElementById('myscript-app-key').value;
  const hmac_key = document.getElementById('myscript-hmac-key').value;
  const res = await fetch('/auth/myscript', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ application_key, hmac_key })
  });
  if (res.ok) {
    showSection('upload-section');
  } else {
    showError('MyScript authentication failed');
  }
};

// Upload .rm file
document.getElementById('upload-btn').onclick = async () => {
  showError('');
  const fileInput = document.getElementById('rm-file');
  if (!fileInput.files.length) {
    showError('Please select a .rm file');
    return;
  }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  const res = await fetch('/upload', { method: 'POST', body: formData });
  if (res.ok) {
    const data = await res.json();
    fileId = data.file_id;
    showSection('process-section');
  } else {
    showError('File upload failed');
  }
};

// Trigger processing
document.getElementById('process-btn').onclick = async () => {
  showError('');
  document.getElementById('status').textContent = 'Processing...';
  const res = await fetch('/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId })
  });
  if (res.ok) {
    const data = await res.json();
    responseId = data.response_id;
    if (data.status === 'done' || data.status === 'processing') {
      await pollResponse();
    } else {
      showError('Processing error');
    }
  } else {
    showError('Processing failed');
  }
};

// Poll for AI response
async function pollResponse() {
  let tries = 0;
  while (tries < 20) {
    const res = await fetch(`/response?response_id=${encodeURIComponent(responseId)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.markdown) {
        showSection('response-section');
        renderMarkdown(data.markdown);
        setupDownload(data.raw);
        return;
      }
    }
    await new Promise(r => setTimeout(r, 1500));
    tries++;
    document.getElementById('status').textContent = 'Waiting for AI response...';
  }
  showError('Timed out waiting for AI response');
}

// Render markdown (basic)
function renderMarkdown(md) {
  // Use a markdown parser for better block support
  // Use marked.js if available, otherwise fallback to basic
  let html = "";
  if (window.marked) {
    html = window.marked.parse(md);
  } else {
    html = md
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<b>$1</b>')
      .replace(/\*(.*?)\*/gim, '<i>$1</i>')
      .replace(/\n$/gim, '<br>');
  }

  // Post-process for mermaid blocks: replace ```mermaid ... ``` with <div class="mermaid">...</div>
  html = html.replace(/<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g, function(_, code) {
    return `<div class="mermaid">${code.replace(/</g, "<").replace(/>/g, ">").replace(/&/g, "&")}</div>`;
  });
  // Also handle raw ```mermaid ... ``` if not parsed by markdown
  html = html.replace(/```mermaid\s*([\s\S]*?)```/g, function(_, code) {
    return `<div class="mermaid">${code}</div>`;
  });

  // Insert HTML
  document.getElementById('markdown-viewer').innerHTML = html;

  // Trigger MathJax rendering for LaTeX blocks
  if (window.MathJax && window.MathJax.typesetPromise) {
    MathJax.typesetPromise();
  }

  // Render all mermaid diagrams
  if (window.mermaid) {
    window.mermaid.init(undefined, ".mermaid");
  }
}

// Setup download link for raw response
function setupDownload(raw) {
  const blob = new Blob([raw], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.getElementById('download-raw');
  link.href = url;
  link.style.display = '';
}