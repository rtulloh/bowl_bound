import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import ClockChoices from '../components/ClockChoices'

const pending = { choices: [
  { id: 'clock:timeout:home', label: 'Alpha timeout; play takes 10 seconds', enabled: true },
  { id: 'clock:hurry', label: 'Hurry next snap; play takes 20 seconds', enabled: true },
  { id: 'clock:spike', label: 'Spike next', enabled: false, reason: 'Engine reason' },
] }
const modifiers = pending.choices.map((c, i) => ({ ...c, label: ['Alpha timeout (3)', 'Hurry-up', 'Spike'][i] }))

it('shows only engine-offered modifiers, with no runoff or Continue control', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} onChoose={onChoose} />)
  expect(screen.getAllByRole('radio')).toHaveLength(3)
  expect(screen.queryByRole('radio', { name: /runoff|none/i })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Continue' })).toBeNull()
  expect(onChoose).not.toHaveBeenCalled()
})

it('submits only an intentionally selected engine modifier', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={onChoose} />)
  expect(screen.getAllByRole('radio')).toHaveLength(3)
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

it('does not steal focus when optional modifiers appear', () => {
  const onChoose = vi.fn()
  render(<ClockChoices pending={pending} modifiers={modifiers} onChoose={onChoose} />)
  screen.getByRole('radio', { name: 'Hurry-up' }).focus()
  expect(screen.getByRole('radio', { name: 'Hurry-up' })).toHaveFocus()
})

it('keeps unavailable reasons accessible and in tooltips without expanding the compact row', () => {
  render(<ClockChoices pending={pending} modifiers={modifiers} optional onChoose={vi.fn()} />)
  const spike = screen.getByRole('radio', { name: 'Spike' })
  expect(spike).toBeDisabled()
  expect(spike).toHaveAccessibleDescription('Engine reason')
  expect(spike.closest('label')).toHaveAttribute('title', 'Spike next — Engine reason')
})
