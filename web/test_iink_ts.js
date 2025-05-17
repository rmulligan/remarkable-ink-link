/**
 * Test script for MyScript iink-ts library
 * 
 * This script tests basic connectivity with the MyScript Cloud API
 * using the official iink-ts library.
 */

// Import the iink-ts library
const iink = require('iink-ts');
const fs = require('fs');
require('dotenv').config();

// Get API keys from environment variables
const applicationKey = process.env.MYSCRIPT_APP_KEY;
const hmacKey = process.env.MYSCRIPT_HMAC_KEY;

if (!applicationKey || !hmacKey) {
  console.error('Error: MYSCRIPT_APP_KEY and MYSCRIPT_HMAC_KEY must be set in environment variables or .env file');
  process.exit(1);
}

console.log(`Using MyScript App Key: ${applicationKey.substring(0, 8)}...${applicationKey.substring(applicationKey.length - 8)}`);
console.log(`Using MyScript HMAC Key: ${hmacKey.substring(0, 8)}...${hmacKey.substring(hmacKey.length - 8)}`);

// Create a simple test with mock handwriting strokes
async function runTest() {
  try {
    console.log('\n=== TESTING MYSCRIPT IINK-TS LIBRARY ===\n');
    
    // Create a recognizer with your credentials
    const recognizer = new iink.Recognizer({
      server: {
        applicationKey,
        hmacKey,
        useWindowLocation: false, // Don't use window.location, we're in Node.js
        scheme: 'https',
        host: 'cloud.myscript.com',
        protocol: 'REST', // Use REST API
      },
      // These settings are important for the recognition
      recognitionParams: {
        type: 'TEXT', // TEXT, MATH, DIAGRAM, etc.
        protocol: 'REST', // REST or WEBSOCKET
        lang: 'en_US',
        export: {
          jiix: {
            strokes: true,
            bounding: true
          },
          text: {
            mimeTypes: ['text/plain'],
            strokeLabels: true
          }
        }
      }
    });

    console.log('Recognizer created successfully');
    
    // Create a basic stroke dataset that represents handwritten "hello"
    const baseTime = Date.now();
    const strokes = [
      // 'h' stroke
      {
        id: 'stroke1',
        x: [100, 100, 100, 100, 120, 140, 140, 140],
        y: [100, 120, 140, 160, 160, 160, 140, 120],
        pointerType: 'PEN',
        timestamps: Array.from({ length: 8 }, (_, i) => baseTime + i * 10)
      },
      // 'e' stroke
      {
        id: 'stroke2',
        x: [180, 200, 220, 200, 180, 180, 200, 220],
        y: [140, 130, 140, 150, 160, 140, 140, 140],
        pointerType: 'PEN',
        timestamps: Array.from({ length: 8 }, (_, i) => baseTime + 100 + i * 10)
      },
      // 'l' stroke
      {
        id: 'stroke3',
        x: [240, 240, 240, 240],
        y: [100, 120, 140, 160],
        pointerType: 'PEN',
        timestamps: Array.from({ length: 4 }, (_, i) => baseTime + 200 + i * 10)
      },
      // 'l' stroke
      {
        id: 'stroke4',
        x: [280, 280, 280, 280],
        y: [100, 120, 140, 160],
        pointerType: 'PEN',
        timestamps: Array.from({ length: 4 }, (_, i) => baseTime + 300 + i * 10)
      },
      // 'o' stroke
      {
        id: 'stroke5',
        x: [320, 340, 360, 360, 340, 320, 320],
        y: [140, 120, 140, 160, 180, 160, 140],
        pointerType: 'PEN',
        timestamps: Array.from({ length: 7 }, (_, i) => baseTime + 400 + i * 10)
      }
    ];

    console.log(`Created ${strokes.length} test strokes`);
    
    // Initialize the recognizer with our strokes
    const model = await recognizer.createModel({
      width: 500,
      height: 300,
      convertUnit: 'mm',
      strokesToImport: strokes
    });

    console.log('Model created successfully');
    
    // Perform recognition
    console.log('Sending recognition request...');
    const result = await model.export({ mimeTypes: ['text/plain', 'application/vnd.myscript.jiix'] });
    
    console.log('\n=== RECOGNITION RESULTS ===\n');
    
    // Display the results
    if (result?.['text/plain']) {
      console.log(`Recognized text: ${result['text/plain']}`);
    }
    
    // Save the JIIX result to a file for inspection
    if (result?.['application/vnd.myscript.jiix']) {
      fs.writeFileSync('recognition_result.jiix', JSON.stringify(result['application/vnd.myscript.jiix'], null, 2));
      console.log('JIIX result saved to recognition_result.jiix');
      
      // Also print some parts of the JIIX result
      const jiix = result['application/vnd.myscript.jiix'];
      console.log('\nJIIX result preview:');
      console.log(`- Type: ${jiix.type}`);
      if (jiix.words) {
        console.log(`- Word count: ${jiix.words.length}`);
        console.log(`- Words: ${jiix.words.map(w => w.label).join(' ')}`);
      }
    }
    
    console.log('\n=== TEST COMPLETED SUCCESSFULLY ===');
    return true;
    
  } catch (error) {
    console.error('Error during recognition:', error);
    
    // Try to provide more detailed information about the error
    if (error.response?.data) {
      console.error('API Error details:', JSON.stringify(error.response.data, null, 2));
    }
    
    return false;
  }
}

// Run the test
runTest()
  .then(success => {
    console.log(`\nTest ${success ? 'PASSED' : 'FAILED'}`);
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });