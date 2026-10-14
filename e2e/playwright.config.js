// End-to-end tests for the storefront and the admin, run against the
// local development stack started by scripts/dev.sh (storefront on 5173,
// API on 5000, database = the Neon dev branch).
//
//   scripts/e2e.sh                 everything, at all four widths
//   scripts/e2e.sh --project=w390  one width
//   scripts/e2e.sh -g "SF-SHOP"    tests whose id matches
//
// Every test title starts with an id (SF-…, CU-…, AD-…, AX-…). docs/QA_MATRIX.md
// is filled in from the results by those ids — see scripts/gen_qa_matrix.py.
import { defineConfig } from '@playwright/test'

const baseURL = process.env.E2E_BASE_URL || 'http://localhost:5173'

// The four widths the audit asks for: phone, tablet, laptop, large desktop.
const widths = [
  ['w390', { width: 390, height: 844 }, true],
  ['w768', { width: 768, height: 1024 }, true],
  ['w1280', { width: 1280, height: 800 }, false],
  ['w1920', { width: 1920, height: 1080 }, false],
]

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  globalSetup: './global-setup.js',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  // One worker per width; the tests inside a width run in order, because they
  // share one store (a coupon made by one test is deleted by the next).
  fullyParallel: false,
  workers: 4,
  retries: 0,
  forbidOnly: true,
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL,
    browserName: 'chromium',
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: widths.map(([name, viewport, hasTouch]) => ({ name, use: { viewport, hasTouch } })),
})
