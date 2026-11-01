import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import PlayLog from '../components/PlayLog'
import ResultPanel from '../components/ResultPanel'
import { report } from './fixtures'

it('renders engine-provided highlight tags in both result and log', () => {
  const entry = report({ highlights: [
    'interception_pending', 'interception', 'fumble', 'touchdown', 'conversion', 'breakaway', 'touchback',
  ] })
  render(<><ResultPanel report={entry} /><PlayLog entries={[entry]} /></>)
  for (const label of [
    'Interception decision', 'Interception', 'Fumble', 'Touchdown', 'Conversion', 'Breakaway roll', 'Touchback',
  ]) {
    expect(within(screen.getByTestId('result-panel')).getByText(label)).toBeVisible()
    expect(within(screen.getByTestId('log-entry')).getByText(label)).toBeVisible()
  }
  expect(screen.getAllByLabelText('Play highlights')).toHaveLength(2)
})

it('does not infer highlights from outcome, statistics, trace sections, or timing', () => {
  const entry = report({ outcome: 'touchdown', statistics: { kind: 'interception' },
    timing: { conversion: true }, trace: report().trace.map((step, index) =>
      index === 0 ? { ...step, section: 'fumble_recovery' } : step) })
  render(<PlayLog entries={[entry]} />)
  expect(screen.queryByLabelText('Play highlights')).toBeNull()
})

it('renders conversion only when the engine provides that tag', () => {
  render(<PlayLog entries={[report({ outcome: 'touchdown', timing: { conversion: true },
    highlights: ['conversion'] }),
  report({ outcome: 'declined_interception', statistics: { kind: 'incomplete' } })]} />)
  expect(screen.getByText('Conversion')).toBeVisible()
  expect(screen.queryByText('Touchdown')).toBeNull()
  expect(screen.queryByText('Interception')).toBeNull()
})

it('keeps unsupported reports free of engine highlight tags', () => {
  render(<ResultPanel report={report({ supported: false, outcome: 'touchdown', highlights: [] })} />)
  expect(screen.queryByLabelText('Play highlights')).toBeNull()
})
