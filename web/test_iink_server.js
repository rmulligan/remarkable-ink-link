/**
 * Test script for MyScript recognition using direct REST API calls
 * This works in Node.js without requiring a browser
 */

const https = require('https');
const crypto = require('crypto');
require('dotenv').config();

// Get API keys from environment
const applicationKey = process.env.MYSCRIPT_APP_KEY;
const hmacKey = process.env.MYSCRIPT_HMAC_KEY;

if (!applicationKey || !hmacKey) {
  console.error('Error: MYSCRIPT_APP_KEY and MYSCRIPT_HMAC_KEY must be set in environment variables or .env file');
  process.exit(1);
}

console.log(`Using MyScript App Key: ${applicationKey.substring(0, 8)}...${applicationKey.substring(applicationKey.length - 8)}`);
console.log(`Using MyScript HMAC Key: ${hmacKey.substring(0, 8)}...${hmacKey.substring(hmacKey.length - 8)}`);

/**
 * Generate HMAC signature for MyScript API authentication
 * @param {string} data - JSON string to sign
 * @returns {string} - Base64-encoded HMAC signature
 */
function generateHmac(data) {
  const hmac = crypto.createHmac('sha512', hmacKey);
  hmac.update(data);
  return hmac.digest('base64');
}

/**
 * Create test stroke data that represents handwritten "hello"
 * @returns {Object} - Stroke data in MyScript format
 */
function createTestData() {
  const baseTime = Date.now();
  
  // Create a test payload with strokes that spell "hello"
  return {
    "configuration": {
      "lang": "en_US",
      "text": {
        "guides": {"enable": true},
        "smartGuide": true,
        "margin": {"top": 20, "left": 10, "right": 10},
      },
      "export": {
        "jiix": {
          "bounding-box": true,
          "strokes": true,
          "text": {
            "chars": true,
            "words": true
          }
        }
      }
    },
    "xDPI": 96,
    "yDPI": 96,
    "contentType": "Text",
    "strokeGroups": [
      {
        "penStyle": "color: #000000;\n-myscript-pen-width: 1;",
        "strokes": [
          // 'h' stroke
          {
            "x": [100, 100, 100, 100, 120, 140, 140, 140],
            "y": [100, 120, 140, 160, 160, 160, 140, 120],
            "t": [baseTime, baseTime+10, baseTime+20, baseTime+30, baseTime+40, baseTime+50, baseTime+60, baseTime+70],
            "p": [0.5, 0.6, 0.7, 0.7, 0.6, 0.5, 0.6, 0.7],
            "pointerType": "pen"
          },
          // 'e' stroke
          {
            "x": [180, 200, 220, 200, 180, 180, 200, 220],
            "y": [140, 130, 140, 150, 160, 140, 140, 140],
            "t": [baseTime+100, baseTime+110, baseTime+120, baseTime+130, baseTime+140, baseTime+150, baseTime+160, baseTime+170],
            "p": [0.5, 0.6, 0.7, 0.6, 0.5, 0.5, 0.5, 0.5],
            "pointerType": "pen"
          },
          // 'l' stroke
          {
            "x": [240, 240, 240, 240],
            "y": [100, 120, 140, 160],
            "t": [baseTime+200, baseTime+210, baseTime+220, baseTime+230],
            "p": [0.5, 0.6, 0.7, 0.5],
            "pointerType": "pen"
          },
          // 'l' stroke
          {
            "x": [280, 280, 280, 280],
            "y": [100, 120, 140, 160],
            "t": [baseTime+300, baseTime+310, baseTime+320, baseTime+330],
            "p": [0.5, 0.6, 0.7, 0.5],
            "pointerType": "pen"
          },
          // 'o' stroke
          {
            "x": [320, 340, 360, 360, 340, 320, 320],
            "y": [140, 120, 140, 160, 180, 160, 140],
            "t": [baseTime+400, baseTime+410, baseTime+420, baseTime+430, baseTime+440, baseTime+450, baseTime+460],
            "p": [0.5, 0.6, 0.7, 0.7, 0.6, 0.5, 0.5],
            "pointerType": "pen"
          }
        ]
      }
    ],
    "height": 500,
    "width": 800,
    "conversionState": "DIGITAL_EDIT"
  };
}

/**
 * Send recognition request to MyScript API
 */
function sendRecognitionRequest() {
  // Create test data
  const requestData = createTestData();
  const jsonData = JSON.stringify(requestData);
  
  // Generate HMAC signature
  const hmacSignature = generateHmac(jsonData);
  
  // Set up request options
  const options = {
    hostname: 'cloud.myscript.com',
    port: 443,
    path: '/api/v4.0/iink/batch',
    method: 'POST',
    headers: {
      'Accept': 'application/json,application/vnd.myscript.jiix',
      'Content-Type': 'application/json',
      'applicationKey': applicationKey,
      'hmac': hmacSignature,
      'Content-Length': Buffer.byteLength(jsonData),
      'Origin': 'https://cloud.myscript.com',  // Required for CORS
      'Referer': 'https://cloud.myscript.com/'  // Helps with authorization
    }
  };
  
  console.log('\n=== SENDING RECOGNITION REQUEST ===\n');
  console.log('Request data sample (first stroke):');
  console.log(JSON.stringify(requestData.strokeGroups[0].strokes[0], null, 2));
  
  // Send the request
  const req = https.request(options, (res) => {
    console.log(`\nResponse Status: ${res.statusCode}`);
    console.log(`Response Headers: ${JSON.stringify(res.headers)}`);
    
    let data = '';
    
    res.on('data', (chunk) => {
      data += chunk;
    });
    
    res.on('end', () => {
      console.log('\n=== RECOGNITION RESULTS ===\n');
      
      if (res.statusCode === 200) {
        try {
          const result = JSON.parse(data);
          
          console.log('Recognition successful!');
          
          // Extract and display recognized text
          if (result.result) {
            console.log(`\nRecognized text: "${result.result}"`);
          }
          
          // Display JIIX data if available
          if (result.jiix) {
            console.log('\nJIIX data:');
            console.log(JSON.stringify(result.jiix, null, 2));
          }
          
          // Save the result to a file for inspection
          const fs = require('fs');
          fs.writeFileSync('recognition_result.json', JSON.stringify(result, null, 2));
          console.log('\nFull result saved to recognition_result.json');
          
        } catch (error) {
          console.error('Error parsing response:', error);
          console.log('Raw response:', data);
        }
      } else {
        console.error('Recognition failed!');
        try {
          const errorObj = JSON.parse(data);
          console.error('Error details:', JSON.stringify(errorObj, null, 2));
        } catch (e) {
          console.error('Raw error response:', data);
        }
      }
    });
  });
  
  req.on('error', (error) => {
    console.error('Request error:', error);
  });
  
  // Write data to request body
  req.write(jsonData);
  req.end();
}

// Run the recognition test
sendRecognitionRequest();