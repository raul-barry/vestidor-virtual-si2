const fs = require('fs');
const path = require('path');

const isRender = Boolean(process.env.RENDER);
let apiUrl = process.env.API_URL || process.env.BACKEND_URL || '';

if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
  if (!apiUrl.includes('.')) {
    apiUrl = `${apiUrl}.onrender.com`;
  }
  apiUrl = `https://${apiUrl}`;
}

if (!apiUrl) {
  apiUrl = isRender ? 'https://vestidor-virtual-backend.onrender.com' : 'http://localhost:8000';
}

const stripeKey = process.env.STRIPE_PUBLISHABLE_KEY || '';
const isProd = process.env.NODE_ENV === 'production' || isRender;

const targetDir = path.join(__dirname, 'src', 'environments');
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

const envConfigFile = `export const environment = {
  production: ${isProd},
  API_URL: '${apiUrl.replace(/\/$/, '')}',
  STRIPE_PUBLISHABLE_KEY: '${stripeKey}'
};
`;

fs.writeFileSync(path.join(targetDir, 'environment.ts'), envConfigFile);
fs.writeFileSync(path.join(targetDir, 'environment.prod.ts'), envConfigFile);
fs.writeFileSync(path.join(targetDir, 'environment.production.ts'), envConfigFile);

console.log(`[set-env] Successfully configured API_URL = '${apiUrl}' (production: ${isProd})`);

