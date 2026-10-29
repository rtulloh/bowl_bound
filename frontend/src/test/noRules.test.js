import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// The browser must hold no football decisions, no raw chart reading, and no Paydirt labels.
const SRC = join(__dirname, '..')
const files = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? (e.name === 'test' ? [] : files(join(dir, e.name))) : [join(dir, e.name)])
const sources = files(SRC).filter((f) => /\.(jsx?|css)$/.test(f))
// Attribution comments may name Paydirt (see docs/ATTRIBUTION.md); shipped code and text may not.
const withoutComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')

describe('the UI contains no football rules', () => {
  it.each(sources.map((f) => [f.slice(SRC.length + 1), withoutComments(readFileSync(f, 'utf8'))]))('%s', (_name, text) => {
    expect(text).not.toMatch(/Ln-Plg|O-Tkl|End-Rn|TE\/SL|Sneak|Kneel|Paydirt/)
    expect(text).not.toMatch(/yards_to_go\s*[-+<>]|ball_from_left\s*[-+]|yards\s*>=|priority|Priority/)
    expect(text).not.toMatch(/parseInt|Number\(|Math\.(min|max)/)
  })
})
