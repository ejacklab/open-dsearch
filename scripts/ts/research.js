#!/usr/bin/env node

const https = require('https');

const API_KEY = process.env.GEMINI_API_KEY;
const MODEL = 'gemini-2.0-flash';

function searchGemini(query, limit = 5) {
  return new Promise((resolve, reject) => {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}`;
    
    const postData = JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: `Search for: ${query}` }] }],
      tools: [{ googleSearch: {} }],
      generationConfig: { temperature: 0.0, maxOutputTokens: 1024 }
    });

    const options = {
      hostname: 'generativelanguage.googleapis.com',
      path: `/v1beta/models/${MODEL}:generateContent?key=${API_KEY}`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const chunks = json.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
          const results = chunks.slice(0, limit).map((chunk, i) => ({
            title: chunk.web?.title || `Result ${i+1}`,
            url: chunk.web?.uri || '',
            snippet: `Source for: ${query}`
          }));
          resolve(results);
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function expandQueries(topic) {
  return [
    topic,
    topic + ' official documentation',
    topic + ' github repository',
    topic + ' tutorial',
    topic + ' architecture'
  ];
}

async function main() {
  const topic = process.argv.slice(2).join(' ') || 'LLM agents';
  
  if (!API_KEY) {
    console.log('Error: GEMINI_API_KEY not set');
    process.exit(1);
  }

  console.log(`🔬 TypeScript Research - Topic: ${topic}`);
  console.log('==============================');

  const start = Date.now();
  const queries = expandQueries(topic);
  console.log(`Running ${queries.length} searches...`);

  const promises = queries.map(q => searchGemini(q, 5).catch(() => []));
  const resultsArrays = await Promise.all(promises);
  
  const allResults = resultsArrays.flat();
  const elapsed = Date.now() - start;

  console.log(`\nFound ${allResults.length} total results`);
  console.log(`✓ Research complete in ${(elapsed/1000).toFixed(1)}s`);

  if (allResults.length > 0) {
    console.log('\nTop results:');
    allResults.slice(0, 3).forEach((r, i) => {
      console.log(`${i+1}. ${r.title}`);
      console.log(`   ${r.url}`);
    });
  }
}

main().catch(console.error);
