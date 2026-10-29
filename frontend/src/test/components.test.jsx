import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import FootballField from '../components/FootballField'
import PlayLog from '../components/PlayLog'
import PlaySelector from '../components/PlaySelector'
import ResultPanel from '../components/ResultPanel'
import Scoreboard from '../components/Scoreboard'
import PenaltyChoices from '../components/PenaltyChoices'
import { report, stateView, view } from './fixtures'

describe('Scoreboard', () => {
  it('shows exactly the engine strings', () => {
    render(<Scoreboard view={view()} />)
    expect(screen.getByTestId('situation')).toHaveTextContent('1st and 10')
    expect(screen.getByTestId('spot')).toHaveTextContent('own 35')
    expect(screen.getByTestId('possession')).toHaveTextContent('Alpha Tech')
    expect(screen.getByTestId('home-name')).toHaveTextContent('Alpha Tech')
    expect(screen.getByTestId('away-name')).toHaveTextContent('Beta State')
  })
  it('shows engine status when there is no field state, not a premature Final', () => {
    render(<Scoreboard view={view({ state: null, status: 'Alpha Tech: choose a conversion.' })} />)
    expect(screen.getByTestId('situation')).toHaveTextContent('Alpha Tech: choose a conversion.')
  })
})

describe('FootballField', () => {
  it('places the ball and first-down marker at the engine coordinates', () => {
    render(<FootballField state={stateView()} home="Alpha Tech" away="Beta State" />)
    expect(parseFloat(screen.getByTestId('ball-marker').style.left)).toBeCloseTo(37.8, 6)
    expect(parseFloat(screen.getByTestId('first-down-marker').style.left)).toBeCloseTo(46.2, 6)
  })
  it('flips the ball when the engine says the team attacks left', () => {
    render(<FootballField state={stateView({ attacking: 'left', ball_from_left: 35, first_down_from_left: 25 })} home="A" away="B" />)
    expect(screen.getByTestId('ball-marker').style.transform).toBe('scaleX(-1)')
    expect(parseFloat(screen.getByTestId('first-down-marker').style.left)).toBeCloseTo(29.4, 6)
  })
  it('renders an empty state when there is no field state', () => {
    render(<FootballField state={null} home="A" away="B" />)
    expect(screen.getByTestId('football-field-empty')).toBeInTheDocument()
  })
})

describe('PlaySelector', () => {
  const actions = view().actions.offense
  it('renders one button per engine action with its label', () => {
    render(<PlaySelector title="OFFENSE" prefix="offense" actions={actions} selected="" onSelect={() => {}} disabled={false} />)
    expect(screen.getAllByRole('button')).toHaveLength(3)
    expect(screen.getByTestId('offense-play-9')).toHaveTextContent('Drop Back')
  })
  it('reports the chosen key and marks it selected', () => {
    const onSelect = vi.fn()
    render(<PlaySelector title="OFFENSE" prefix="offense" actions={actions} selected="2" onSelect={onSelect} disabled={false} />)
    fireEvent.click(screen.getByTestId('offense-play-1'))
    expect(onSelect).toHaveBeenCalledWith('1')
    expect(screen.getByTestId('offense-play-2').className).toContain('play-button-selected')
  })
  it('does nothing when disabled', () => {
    const onSelect = vi.fn()
    render(<PlaySelector title="OFFENSE" prefix="offense" actions={actions} selected="" onSelect={onSelect} disabled />)
    fireEvent.click(screen.getByTestId('offense-play-1'))
    expect(onSelect).not.toHaveBeenCalled()
  })
})

describe('ResultPanel', () => {
  it('prompts before any play', () => {
    render(<ResultPanel report={null} />)
    expect(screen.getByTestId('result-empty')).toBeInTheDocument()
  })
  it('shows the engine description and the real dice trace', () => {
    render(<ResultPanel report={report()} />)
    expect(screen.getByTestId('result-description')).toHaveTextContent('gain of 6 yards')
    expect(screen.getByTestId('trace')).toHaveTextContent('dice 1+2+3 = 15, cell 4')
    expect(screen.queryByTestId('unsupported-notice')).toBeNull()
    expect(screen.queryByTestId('resolved-play')).toBeNull()
  })
  it('says honestly when a result is not supported yet', () => {
    render(<ResultPanel report={report({ supported: false, unsupported_reason: 'interception' })} />)
    expect(screen.getByTestId('unsupported-notice')).toHaveTextContent('Not yet supported: interception')
  })
  it('shows both the called and the resolved play for an option', () => {
    render(<ResultPanel report={report({ called_play: 'Option', resolved_play: 'Sprint Out' })} />)
    expect(screen.getByTestId('resolved-play')).toHaveTextContent('Called Option; resolved as Sprint Out')
  })
})

describe('PenaltyChoices', () => {
  const pending = {
    choices: [
      { id: 'accept', label: 'Accept penalty', enabled: true },
      { id: 'decline', label: 'Decline penalty', enabled: false, reason: 'This choice is unavailable' },
    ],
  }

  it('renders engine labels and forwards the selected choice id', () => {
    const onChoose = vi.fn()
    render(<PenaltyChoices pending={pending} onChoose={onChoose} />)

    fireEvent.click(screen.getByTestId('penalty-choice-accept'))

    expect(screen.getByTestId('penalty-choice-accept')).toHaveTextContent('Accept penalty')
    expect(onChoose).toHaveBeenCalledWith('accept')
  })

  it('disables unavailable choices and shows their engine reason', () => {
    render(<PenaltyChoices pending={pending} onChoose={() => {}} />)

    expect(screen.getByTestId('penalty-choice-decline')).toBeDisabled()
    expect(screen.getByTestId('penalty-choice-decline-reason')).toHaveTextContent('This choice is unavailable')
  })
})

describe('PlayLog', () => {
  it('renders nothing when empty and lists the engine descriptions otherwise', () => {
    const { container, rerender } = render(<PlayLog entries={[]} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<PlayLog entries={[report(), report({ number: 2, description: 'second play' })]} />)
    expect(screen.getAllByTestId('log-entry')).toHaveLength(2)
    expect(screen.getAllByTestId('log-entry')[1]).toHaveTextContent('2. second play')
  })
})


it('shows engine-provided score values', () => {
  render(<Scoreboard view={view({ score: { home: 7, away: 6 } })} />)
  expect(screen.getByTestId('home-score')).toHaveTextContent('7')
  expect(screen.getByTestId('away-score')).toHaveTextContent('6')
})


it('does not reserve an empty panel for unavailable play groups', () => {
  const { container } = render(<PlaySelector title="OFFENSE" prefix="offense" actions={[]} selected="" onSelect={() => {}} disabled />)
  expect(container).toBeEmptyDOMElement()
})
