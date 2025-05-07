/**
 * InkLink Web UI Logic with Multi-Page Navigation, Context Visualization, and Manual Linking
 */

let fileId = null;
let responseId = null;

// --- Multi-page and linking state ---
let pageContents = [];      // Array of markdown for each page
let currentPage = 1;        // 1-based index
let totalPages = 1;
let links = [];             // Array of {from, to, desc}

// --- DOM Elements ---
const pageNav = document.getElementById('page-nav');
const prevPageBtn = document.getElementById('prev-page-btn');
const nextPageBtn = document.getElementById('next-page-btn');
const pageNumInput = document.getElementById('page-num-input');
const totalPagesSpan = document.getElementById('total-pages');
const contextPanel = document.getElementById('context-visualization');
const contextContent = document.getElementById('context-content');
const linkControls = document.getElementById('link-controls');
const linkList = document.getElementById('link-list');
const addLinkBtn = document.getElementById('add-link-btn');
const addLinkPanel = document.getElementById('add-link-panel');
const linkFromInput = document.getElementById('link-from');
const linkToInput = document.getElementById('link-to');
const linkDescInput = document.getElementById('link-desc');
const saveLinkBtn = document.getElementById('save-link-btn');
const cancelLinkBtn = document.getElementById('cancel-link-btn');

// --- Helper: Show/hide navigation, context, and linking controls ---
function showPageUI(show) {
  if (pageNav) {
  if (contextPanel) {
  if (linkControls) {
}

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
  const errorElement = document.getElementById('error');
  if (errorElement) {
    errorElement.textContent = msg || '';
  }
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
    showError('Please select a file');
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

/**
 * Poll for AI response and initialize multi-page UI if markdown is received.
 */
async function pollResponse() {
  let tries = 0;
  while (tries < 20) {
    const res = await fetch(`/response?response_id=${encodeURIComponent(responseId)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.markdown) {
        showSection('response-section');
        // --- Split markdown into pages (delimiter: '\n---PAGE---\n' or fallback to single page) ---
        pageContents = data.markdown.split(/\n-{3,}PAGE-{3,}\n/);
        totalPages = pageContents.length;
        currentPage = 1;
        links = []; // Reset links for new doc
        renderCurrentPage();
        setupDownload(data.raw);
        // Show navigation/context/linking UI if multi-page
        showPageUI(totalPages > 1);
        return;
      }
    }
    await new Promise(r => setTimeout(r, 1500));
    tries++;
    document.getElementById('status').textContent = 'Waiting for AI response...';
  }
  showError('Timed out waiting for AI response');
}

/**
 * Render the current page's markdown and update navigation/context/linking UI.
 */
function renderCurrentPage() {
  // Clamp currentPage
  if (currentPage < 1) currentPage = 1;
  if (currentPage > totalPages) currentPage = totalPages;
  // Update nav UI
  pageNumInput.value = currentPage;
  totalPagesSpan.textContent = totalPages;
  if (prevPageBtn) {
  if (nextPageBtn) {

  // Render markdown for current page
  renderMarkdown(pageContents[currentPage - 1] || '');

  // Render context for current page
  renderContext();

  // Render links for current page
  renderLinks();
}

/**
 * Render markdown (basic or using marked.js if available)
 */
function renderMarkdown(md) {
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

  // Mermaid block handling
  html = html.replace(/<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g, function(_, code) {
    return `<div class="mermaid">${code.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/&/g, "&amp;")}</div>`;
  });
  html = html.replace(/```mermaid\s*([\s\S]*?)```/g, function(_, code) {
    return `<div class="mermaid">${code}</div>`;
  });

  const markdownViewer = document.getElementById('markdown-viewer');
  if (markdownViewer) {
    markdownViewer.innerHTML = html;
  }

  // MathJax and Mermaid rendering
  if (window.MathJax && window.MathJax.typesetPromise) MathJax.typesetPromise();
  if (window.mermaid) window.mermaid.init(undefined, ".mermaid");
}

/**
 * Render context visualization for the current page.
 * Shows links from/to this page.
 */
function renderContext() {
  if (!contextContent) {
  
  const fromLinks = links.filter(l => l.from === currentPage);
  const toLinks = links.filter(l => l.to === currentPage);
  let html = '';
  if (fromLinks.length) {
    html += `<div><b>Links from this page:</b><ul>` +
      fromLinks.map(l => `<li>To page ${l.to}: ${l.desc || ''}</li>`).join('') +
      `</ul></div>`;
  }
  if (toLinks.length) {
    html += `<div><b>Links to this page:</b><ul>` +
      toLinks.map(l => `<li>From page ${l.from}: ${l.desc || ''}</li>`).join('') +
      `</ul></div>`;
  }
  if (!html) html = '<i>No links for this page.</i>';
  contextContent.innerHTML = html;
}

/**
 * Render the list of all cross-page links and add remove buttons.
 */
function renderLinks() {
  if (!linkList) {
  
  linkList.innerHTML = '';
  links.forEach((l, idx) => {
    const li = document.createElement('li');
    li.textContent = `Page ${l.from} → Page ${l.to}: ${l.desc || ''}`;
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Remove';
    delBtn.style.marginLeft = '1em';
    delBtn.onclick = () => {
      links.splice(idx, 1);
      renderCurrentPage();
    };
    li.appendChild(delBtn);
    linkList.appendChild(li);
  });
}

/**
 * Setup download link for raw response
 */
function setupDownload(raw) {
  const downloadLink = document.getElementById('download-raw');
  if (!downloadLink) {
  
  const blob = new Blob([raw], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  downloadLink.href = url;
  downloadLink.style.display = '';
}

// --- Navigation event handlers ---
if (pageNav) {
  if (prevPageBtn) {
    prevPageBtn.onclick = () => {
      if (currentPage > 1) {
        currentPage--;
        renderCurrentPage();
      }
    };
  }
  
  if (nextPageBtn) {
    nextPageBtn.onclick = () => {
      if (currentPage < totalPages) {
        currentPage++;
        renderCurrentPage();
      }
    };
  }
  
  if (pageNumInput) {
    pageNumInput.onchange = () => {
      let val = parseInt(pageNumInput.value, 10);
      if (isNaN(val) || val < 1) {
      if (val > totalPages) {
      currentPage = val;
      renderCurrentPage();
    };
  }
}

// --- Manual linking controls ---
if (linkControls) {
  if (addLinkBtn) {
    addLinkBtn.onclick = () => {
      if (addLinkPanel) {
        addLinkPanel.style.display = '';
        if (linkFromInput) {
        if (linkToInput) {
        if (linkDescInput) {
      }
    };
  }
  
  if (cancelLinkBtn) {
    cancelLinkBtn.onclick = () => {
      if (addLinkPanel) addLinkPanel.style.display = 'none';
    };
  }
  
  if (saveLinkBtn) {
    saveLinkBtn.onclick = () => {
      const from = parseInt(linkFromInput.value, 10);
      const to = parseInt(linkToInput.value, 10);
      const desc = linkDescInput.value.trim();
      if (
        isNaN(from) || isNaN(to) ||
        from < 1 || from > totalPages ||
        to < 1 || to > totalPages ||
        from === to
      ) {
        showError('Invalid link: check page numbers.');
        return;
      }
      links.push({ from, to, desc });
      if (addLinkPanel) addLinkPanel.style.display = 'none';
      showError('');
      renderCurrentPage();
    };
  }
}