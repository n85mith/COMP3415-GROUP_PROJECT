const { existsSync } = require('node:fs');
const { defineConfig } = require('@playwright/test');

const venvPython = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
const python = process.env.CARESIGHT_PYTHON || (existsSync(venvPython) ? venvPython : 'python');
const baseURL = 'http://127.0.0.1:8767';

module.exports = defineConfig({
  testDir: './browser_tests',
  workers: 1,
  use: { baseURL, browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: {
    command: `"${python}" -m browser_tests.serve`,
    url: baseURL,
    reuseExistingServer: false,
  },
});
