import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ResultPanel from '../components/ResultPanel'
import PlayLog from '../components/PlayLog'
import { report } from './fixtures'

describe('engine-owned narration', () => {
  it.each([false, true])('uses exact engine text in live/log with pending=%s', (pending) => {
    const commentary = 'Away <img src=x onerror=alert(1)> ' + 'Q'.repeat(100) + ' is stopped for no gain!'
    const entry = report({ commentary, pending, description: 'Legacy semantic facts' })
    const { container } = render(<><ResultPanel report={entry} /><PlayLog entries={[entry]} /></>)
    expect(screen.getByTestId('result-description').textContent).toBe(commentary)
    expect(screen.getByTestId('log-entry').textContent).toContain('1. ' + commentary)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByTestId('result-description')).toHaveClass('break-words')
  })
  it.each([undefined, null])('falls back to legacy text for missing commentary=%s', (commentary) => {
    const entry = report({ commentary, description: 'Generic engine wording.' })
    render(<><ResultPanel report={entry} /><PlayLog entries={[entry]} /></>)
    expect(screen.getByTestId('result-description')).toHaveTextContent('Generic engine wording.')
    expect(screen.getByTestId('log-entry')).toHaveTextContent('1. Generic engine wording.')
  })
})
