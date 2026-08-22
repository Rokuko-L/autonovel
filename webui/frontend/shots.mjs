// Screenshot every screen of the running dev server for self-review.
// Usage: node shots.mjs [baseUrl]
import { chromium } from 'playwright-core'
import { readdirSync } from 'node:fs'

const base = process.argv[2] ?? 'http://localhost:5175'
const outDir = '/tmp/opencode/shots'
readdirSync('/tmp/opencode', { recursive: false }) // ensure dir exists via mkdir below
const { mkdirSync } = await import('node:fs')
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch({
  executablePath: `${process.env.HOME}/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`,
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto(base, { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)

const tabs = ['projects', 'foundation', 'beats & harvests', 'live run', 'llm inspector', 'costs', 'settings']
for (const label of tabs) {
  await page.getByRole('button', { name: new RegExp(label, 'i') }).first().click()
  await page.waitForTimeout(label === 'beats & harvests' ? 2600 : 1400)
  const file = `${outDir}/${label.replace(/[^a-z]+/g, '_')}.png`
  await page.screenshot({ path: file })
  console.log('shot', file)
}
await browser.close()
