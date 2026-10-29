import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import PlayLog from '../components/PlayLog'
import ResultPanel from '../components/ResultPanel'
import { report } from './fixtures'

const traceStep = (section) => ({ ...report().trace[0], section })

it.each([
  ['interception', { statistics: { kind: 'interception' } }, 'Interception'],
  ['pending interception', { outcome: 'interception_pending', pending: true }, 'Interception decision'],
  ['fumble touchback', { outcome: 'touchback', trace: [traceStep('fumble_recovery')] }, 'Fumble'],
  ['touchdown', { outcome: 'touchdown' }, 'Touchdown'],
  ['defensive touchdown', { outcome: 'defensive_touchdown' }, 'Touchdown'],
  ['breakaway', { trace: [traceStep('supplemental:B')] }, 'Breakaway roll'],
])('emphasizes %s using recorded structured facts in both result and log', (_name, facts, label) => {
  const entry = report(facts)
  render(<><ResultPanel report={entry} /><PlayLog entries={[entry]} /></>)
  expect(within(screen.getByTestId('result-panel')).getByText(label)).toBeVisible()
  expect(within(screen.getByTestId('log-entry')).getByText(label)).toBeVisible()
  expect(screen.getAllByLabelText('Play highlights')).toHaveLength(2)
})

it('shows both fumble and touchback without rewriting the engine description', () => {
  const entry = report({ outcome: 'touchback', description: 'Engine touchback description.',
    trace: [traceStep('fumble_recovery')] })
  render(<PlayLog entries={[entry]} />)
  const highlights = screen.getByLabelText('Play highlights')
  expect(within(highlights).getByText('Fumble')).toBeVisible()
  expect(within(highlights).getByText('Touchback')).toBeVisible()
  expect(screen.getByText('1. Engine touchback description.')).toBeVisible()
})

it('does not infer dramatic outcomes from prose, raw cells, or yardage', () => {
  render(<PlayLog entries={[report({ yards: 60,
    description: 'Touchdown interception fumble breakaway',
    trace: [{ ...traceStep('offense'), cell: 'F + 2' }] })]} />)
  expect(screen.queryByLabelText('Play highlights')).toBeNull()
})

it('does not call a conversion a touchdown or a declined interception a turnover', () => {
  render(<PlayLog entries={[report({ number: 1, outcome: 'touchdown', timing: { conversion: true } }),
    report({ number: 2, outcome: 'declined_interception', statistics: { kind: 'incomplete' } })]} />)
  expect(screen.getByText('Conversion')).toBeVisible()
  expect(screen.queryByText('Touchdown')).toBeNull()
  expect(screen.queryByText('Interception')).toBeNull()
})

it('does not emphasize an unsupported/unapplied report', () => {
  render(<ResultPanel report={report({ supported: false, outcome: 'touchdown' })} />)
  expect(screen.queryByLabelText('Play highlights')).toBeNull()
})
