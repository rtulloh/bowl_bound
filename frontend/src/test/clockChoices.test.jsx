import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import ClockChoices from '../components/ClockChoices'

const pending = { choices: [
  { id: 'clock:runoff', label: 'Run 30 seconds off the clock', enabled: true },
  { id: 'clock:timeout:home', label: 'Alpha timeout; play takes 10 seconds', enabled: true },
  { id: 'clock:hurry', label: 'Hurry next snap; play takes 20 seconds', enabled: true },
  { id: 'clock:spike', label: 'Spike next', enabled: false, reason: 'Engine reason' },
] }
const modifiers = pending.choices.map((c, i) => ({ ...c, label: ['None', 'Alpha timeout (3)', 'Hurry-up', 'Spike'][i] }))

it('defaults to None and requires no Continue or submission for ordinary play', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={onChoose} />)
  expect(screen.getByRole('radio', { name: 'None' })).toBeChecked()
  expect(screen.queryByRole('button', { name: 'Continue' })).toBeNull()
  fireEvent.click(screen.getByRole('radio', { name: 'None' }))
  expect(onChoose).not.toHaveBeenCalled()
})

it('submits only an intentionally selected engine modifier', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={onChoose} />)
  expect(screen.getAllByRole('radio')).toHaveLength(4)
  expect(screen.getByRole('radio', { name: 'Spike' })).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Hurry-up' }))
  expect(onChoose).toHaveBeenCalledWith('clock:hurry')
})

it('disables modifier submissions while a request is in flight', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={onChoose} disabled />)
  for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Hurry-up' }))
  expect(onChoose).not.toHaveBeenCalled()
})

it('keeps explicit Continue at a period boundary, before spending any time', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} optional={false} onChoose={onChoose} />)
  expect(screen.getByText('Engine reason')).toBeInTheDocument()
  expect(onChoose).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  expect(onChoose).toHaveBeenCalledWith('clock:runoff')
})

it('applies persistent mode at a required boundary only when hurry is engine-offered', () => {
  const onChoose = vi.fn()
  const { rerender } = render(<ClockChoices pending={pending} modifiers={modifiers} hurryMode onChoose={onChoose} />)
  fireEvent.click(screen.getByRole('button', { name: 'Continue with hurry-up' }))
  expect(onChoose).toHaveBeenLastCalledWith('clock:hurry')
  const noHurry = { choices: pending.choices.filter((c) => c.id !== 'clock:hurry') }
  rerender(<ClockChoices pending={noHurry} hurryMode onChoose={onChoose} />)
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  expect(onChoose).toHaveBeenLastCalledWith('clock:runoff')
})

it('focuses required continuation but does not steal focus for optional controls', () => {
  const onChoose = vi.fn()
  const { rerender } = render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={onChoose} />)
  screen.getByRole('radio', { name: 'None' }).focus()
  expect(screen.getByRole('radio', { name: 'None' })).toHaveFocus()
  rerender(<ClockChoices pending={pending} modifiers={modifiers} onChoose={onChoose} />)
  expect(screen.getByRole('button', { name: 'Continue' })).toHaveFocus()
})

it('keeps unavailable reasons accessible and in tooltips without expanding the compact row', () => {
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={vi.fn()} />)
  const spike = screen.getByRole('radio', { name: 'Spike' })
  expect(spike).toBeDisabled()
  expect(spike).toHaveAccessibleDescription('Engine reason')
  expect(spike.closest('label')).toHaveAttribute('title', 'Spike next — Engine reason')
})
