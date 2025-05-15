/**
 * Simple server to serve the iink-ts test HTML file with API keys
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Get API keys from environment variables
const applicationKey = process.env.MYSCRIPT_APP_KEY;
const hmacKey = process.env.MYSCRIPT_HMAC_KEY;

if (!applicationKey || !hmacKey) {
  console.error('Error: MYSCRIPT_APP_KEY and MYSCRIPT_HMAC_KEY must be set in environment variables or .env file');
  process.exit(1);
}

// Create a server
const server = http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html' || req.url === '/test_iink.html') {
    // Read the HTML file
    fs.readFile(path.join(__dirname, 'test_iink.html'), 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Error loading HTML file');
        return;
      }
      
      // Replace placeholders with actual keys
      const html = data
        .replace('MYSCRIPT_APP_KEY_PLACEHOLDER', applicationKey)
        .replace('MYSCRIPT_HMAC_KEY_PLACEHOLDER', hmacKey);
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(html);
    });
  } else if (req.url.startsWith('/node_modules/')) {
    // Serve files from node_modules
    const filePath = path.join(__dirname, req.url);
    
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('File not found');
        return;
      }
      
      let contentType = 'text/plain';
      if (req.url.endsWith('.js')) {
        contentType = 'application/javascript';
      } else if (req.url.endsWith('.css')) {
        contentType = 'text/css';
      }
      
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    });
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
});

// Start the server
const PORT = 3000;
server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}/`);
  console.log(`Using MyScript App Key: ${applicationKey.substring(0, 8)}...${applicationKey.substring(applicationKey.length - 8)}`);
  console.log(`Using MyScript HMAC Key: ${hmacKey.substring(0, 8)}...${hmacKey.substring(hmacKey.length - 8)}`);
});