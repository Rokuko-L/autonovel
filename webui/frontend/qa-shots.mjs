// Screenshot every view of the restructured console for self-review.
// Usage: node qa-shots.mjs [baseUrl] [outDir]
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'

const base = process.argv[2] ?? 'http://localhost:5175'
const outDir = process.argv[3] ?? 'qa'
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const shot = async (hash, name, wait = 1500) => {
  await page.goto(`${base}/${hash}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(wait)
  await page.screenshot({ path: `${outDir}/${name}.png` })
  console.log('shot', name)
}

await shot('#/projects', '01_landing', 2500)

// wizard — open + first step
await page.getByRole('button', { name: /new project/i }).first().click()
await page.waitForTimeout(800)
await page.screenshot({ path: `${outDir}/02_wizard.png` })
console.log('shot 02_wizard')
await page.keyboard.press('Escape')
await page.goto(`${base}/#/projects`, { waitUntil: 'networkidle' })
await page.waitForTimeout(400)

const PROJECT = 'smoke_4ch'
await shot(`#/p/${PROJECT}`, '03_overview')
await shot(`#/p/${PROJECT}/pipeline/run`, '04_pipeline_run', 2200)
await shot(`#/p/${PROJECT}/pipeline/scores`, '05_pipeline_scores')
await shot(`#/p/${PROJECT}/pipeline/evals`, '06_pipeline_evals', 2200)
await shot(`#/p/${PROJECT}/pipeline/llm`, '07_pipeline_llm', 2200)
await shot(`#/p/${PROJECT}/pipeline/telemetry`, '08_pipeline_telemetry', 2000)
await shot(`#/p/${PROJECT}/foundation/graph`, '09_foundation_graph', 2500)
await shot(`#/p/${PROJECT}/foundation/world`, '10_foundation_world')
await shot(`#/p/${PROJECT}/manuscript`, '11_manuscript', 2500)
await shot(`#/p/${PROJECT}/revision`, '12_revision', 2200)
await shot(`#/p/${PROJECT}/ledger`, '13_ledger', 2000)
await shot(`#/p/${PROJECT}/arena`, '14_arena', 2200)
await shot('#/settings', '15_settings', 2000)

await browser.close()
