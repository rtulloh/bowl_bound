import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import TeamPicker from '../components/TeamPicker'

const catalog = [
  { id: '2007/cedar-valley', name: 'Cedar Valley', season: 2007 },
  { id: '2007/harbor-tech', name: 'Harbor Tech', season: 2007 },
  { id: '2007/alpha-tech', name: 'Alpha Tech', season: 2007 },
  { id: '2012/harbor-tech', name: 'Harbor Tech', season: 2012 },
  { id: '2012/lakeside', name: 'Lakeside', season: 2012 },
  ...Array.from({ length: 20 }, (_, index) => ({
    id: `2007/filler-${index}`,
    name: `Filler ${String(index).padStart(2, '0')}`,
    season: 2007,
  })),
]

function setup(props = {}) {
  const onSelect = vi.fn()
  const view = render(
    <TeamPicker
      label="Home team"
      teams={catalog}
      season="2007"
      value="2007/cedar-valley"
      onSelect={onSelect}
      {...props}
    />,
  )
  return { onSelect, view }
}

function open() {
  const combobox = screen.getByRole('combobox', { name: 'Home team' })
  fireEvent.click(combobox)
  return combobox
}

it('shows the season-qualified identity on the closed control', () => {
  setup()
  expect(screen.getByRole('combobox', { name: 'Home team' })).toHaveValue('2007 Cedar Valley')
})

it('lists only the selected season sorted by name when opened', () => {
  setup()
  open()
  const options = within(screen.getByRole('listbox')).getAllByRole('option')
  const names = options.map((o) => o.textContent)
  expect(names.slice(0, 2)).toEqual(['Alpha Tech 2007', 'Cedar Valley 2007'])
  expect(names).toContain('Harbor Tech 2007')
  expect(names.every((name) => name.endsWith('2007'))).toBe(true)
  expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)))
})

it('filters by team name and by slug', () => {
  setup()
  const combobox = open()
  fireEvent.change(combobox, { target: { value: 'harbor' } })
  expect(within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent))
    .toEqual(['Harbor Tech 2007'])
  fireEvent.change(combobox, { target: { value: 'alpha-tech' } })
  expect(within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent))
    .toEqual(['Alpha Tech 2007'])
})

it('offers an all-seasons search that selects year and team together', () => {
  const { onSelect } = setup()
  const combobox = open()
  fireEvent.click(screen.getByRole('button', { name: /search all seasons/i }))
  fireEvent.change(combobox, { target: { value: 'lakeside' } })
  fireEvent.click(screen.getByRole('option', { name: /Lakeside 2012/ }))
  expect(onSelect).toHaveBeenCalledWith({ id: '2012/lakeside', name: 'Lakeside', season: 2012 })
})

it('shows the same school in two years as two distinct results', () => {
  setup()
  const combobox = open()
  fireEvent.click(screen.getByRole('button', { name: /search all seasons/i }))
  fireEvent.change(combobox, { target: { value: 'harbor' } })
  const options = within(screen.getByRole('listbox')).getAllByRole('option')
  expect(options.map((o) => o.textContent)).toEqual(['Harbor Tech 2007', 'Harbor Tech 2012'])
})

it('supports arrow keys, Enter and Escape with focus returning to the combobox', () => {
  const { onSelect } = setup()
  const combobox = open()
  fireEvent.change(combobox, { target: { value: 'harbor' } })
  fireEvent.keyDown(combobox, { key: 'ArrowDown' })
  fireEvent.keyDown(combobox, { key: 'Enter' })
  expect(onSelect).toHaveBeenCalledWith({ id: '2007/harbor-tech', name: 'Harbor Tech', season: 2007 })
  expect(combobox).toHaveFocus()

  open()
  fireEvent.keyDown(screen.getByRole('combobox', { name: 'Home team' }), { key: 'Escape' })
  expect(screen.queryByRole('listbox')).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Home team' })).toHaveFocus()
})

it('exposes combobox state and an active descendant on the focused control', () => {
  setup()
  const combobox = screen.getByRole('combobox', { name: 'Home team' })
  expect(combobox).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(combobox)
  expect(combobox).toHaveAttribute('aria-expanded', 'true')
  expect(combobox).toHaveFocus()
  const listbox = screen.getByRole('listbox')
  expect(combobox).toHaveAttribute('aria-controls', listbox.id)
  fireEvent.keyDown(combobox, { key: 'ArrowDown' })
  const active = combobox.getAttribute('aria-activedescendant')
  expect(active).toBeTruthy()
  expect(document.getElementById(active)).toHaveAttribute('role', 'option')
})

it('scrolls the active option into view during keyboard navigation', () => {
  const scrollIntoView = vi.fn()
  Element.prototype.scrollIntoView = scrollIntoView
  setup()
  const combobox = open()
  fireEvent.keyDown(combobox, { key: 'ArrowDown' })
  expect(scrollIntoView).toHaveBeenCalled()
})

it('closes and stops accepting selections when disabled while open', () => {
  const onSelect = vi.fn()
  const { view } = setup({ onSelect })
  open()
  expect(screen.getByRole('listbox')).toBeInTheDocument()
  view.rerender(
    <TeamPicker
      label="Home team"
      teams={catalog}
      season="2007"
      value="2007/cedar-valley"
      onSelect={onSelect}
      disabled
    />,
  )
  expect(screen.queryByRole('listbox')).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Home team' })).toBeDisabled()
})

it('resets search and season scope when dismissed by an outside click', () => {
  setup()
  const combobox = open()
  fireEvent.click(screen.getByRole('button', { name: /search all seasons/i }))
  fireEvent.change(combobox, { target: { value: 'lakeside' } })
  fireEvent.mouseDown(document.body)
  expect(screen.queryByRole('listbox')).toBeNull()

  fireEvent.click(screen.getByRole('combobox', { name: 'Home team' }))
  expect(screen.getByRole('combobox', { name: 'Home team' })).toHaveValue('')
  const options = within(screen.getByRole('listbox')).getAllByRole('option')
  expect(options.every((option) => option.textContent.endsWith('2007'))).toBe(true)
})

it('falls back to a native select for small catalogs', () => {
  const onSelect = vi.fn()
  render(
    <TeamPicker
      label="Home team"
      teams={catalog.slice(0, 2)}
      season="2007"
      value="2007/cedar-valley"
      onSelect={onSelect}
      smallCatalogLimit={10}
    />,
  )
  const select = screen.getByLabelText('Home team')
  expect(select.tagName).toBe('SELECT')
  fireEvent.change(select, { target: { value: '2007/harbor-tech' } })
  expect(onSelect).toHaveBeenCalledWith({ id: '2007/harbor-tech', name: 'Harbor Tech', season: 2007 })
})
