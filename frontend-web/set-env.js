const fs = require('fs');
const path = require('path');

let apiUrl = process.env.API_URL || process.env.BACKEND_URL || 'http://localhost:8000';
if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
  apiUrl = `https://${apiUrl}`;
}
const isProd = process.env.NODE_ENV === 'production' || Boolean(process.env.RENDER);

const targetDir = path.join(__dirname, 'src', 'environments');
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

const envConfigFile = `export const environment = {
  production: ${isProd},
  API_URL: '${apiUrl.replace(/\/$/, '')}'
};
`;

fs.writeFileSync(path.join(targetDir, 'environment.ts'), envConfigFile);
fs.writeFileSync(path.join(targetDir, 'environment.prod.ts'), envConfigFile);

console.log(`[set-env] Successfully configured API_URL = '${apiUrl}' (production: ${isProd})`);
