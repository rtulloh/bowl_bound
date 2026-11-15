import { useEffect, useId, useMemo, useRef, useState } from 'react'

const DEFAULT_SMALL_CATALOG_LIMIT = 12

function slugOf(teamId) {
  return teamId ? teamId.split('/')[1] : ''
}

function matches(team, query) {
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  return team.name.toLowerCase().includes(needle) || slugOf(team.id).includes(needle)
}

function byName(a, b) {
  return a.name.localeCompare(b.name) || String(a.season).localeCompare(String(b.season))
}

/**
 * Searchable, season-scoped team picker.
 *
 * The focused input is the combobox, so `aria-activedescendant` describes the
 * option the user is actually navigating. Falls back to a native select for
 * small catalogs, where a combobox would add interaction cost without helping
 * discovery.
 */
export default function TeamPicker({
  label,
  teams,
  season,
  value,
  onSelect,
  disabled,
  smallCatalogLimit = DEFAULT_SMALL_CATALOG_LIMIT,
  testId,
}) {
  const listId = useId()
  const inputRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [allSeasons, setAllSeasons] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const selected = useMemo(() => teams.find((team) => team.id === value), [teams, value])
  const scoped = useMemo(
    () => teams.filter((team) => allSeasons || String(team.season) === String(season)),
    [teams, season, allSeasons],
  )
  const results = useMemo(() => scoped.filter((team) => matches(team, query)).sort(byName), [scoped, query])

  const reset = () => {
    setQuery('')
    setAllSeasons(false)
    setActiveIndex(0)
  }

  const close = ({ restoreFocus = true } = {}) => {
    setOpen(false)
    reset()
    if (restoreFocus) inputRef.current?.focus()
  }

  // A disabled picker must not stay interactive behind an open popup.
  useEffect(() => {
    if (disabled && open) close({ restoreFocus: false })
  }, [disabled, open])

  useEffect(() => {
    if (!open) return
    setActiveIndex(0)
    inputRef.current?.focus()
  }, [open, query, allSeasons])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event) => {
      if (!inputRef.current?.parentElement?.contains(event.target)) {
        close({ restoreFocus: false })
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [open])

  const activeId = results[activeIndex] ? `${listId}-option-${activeIndex}` : undefined

  // Keep the highlighted option visible during keyboard navigation.
  useEffect(() => {
    if (!open || !activeId) return
    document.getElementById(activeId)?.scrollIntoView?.({ block: 'nearest' })
  }, [open, activeId])

  const choose = (team) => {
    if (disabled) return
    onSelect(team)
    close()
  }

  const openPicker = () => {
    if (disabled) return
    reset()
    setOpen(true)
  }

  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      if (!open) return
      event.preventDefault()
      close()
      return
    }
    if (!open) {
      if (event.key === 'ArrowDown' || event.key === 'Enter') {
        event.preventDefault()
        openPicker()
      }
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (!results.length) return
      const delta = event.key === 'ArrowDown' ? 1 : -1
      setActiveIndex((current) => (current + delta + results.length) % results.length)
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      const team = results[activeIndex]
      if (team) choose(team)
    }
  }

  if (teams.length <= smallCatalogLimit) {
    const scopedTeams = [...teams]
      .filter((team) => String(team.season) === String(season))
      .sort(byName)
    return (
      <label className="block">
        {label}
        <select
          className="block w-full text-black p-1"
          value={value}
          onChange={(event) => {
            const team = teams.find((candidate) => candidate.id === event.target.value)
            onSelect(team || null)
          }}
          disabled={disabled}
          data-testid={testId}
        >
          <option value="">Choose a team</option>
          {scopedTeams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.season} {team.name}
            </option>
          ))}
        </select>
      </label>
    )
  }

  return (
    <div className="block">
      <span className="block">{label}</span>
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-haspopup="listbox"
        aria-autocomplete="list"
        aria-activedescendant={open ? activeId : undefined}
        aria-label={label}
        className="block w-full text-black bg-white p-1"
        value={open ? query : selected ? `${selected.season} ${selected.name}` : ''}
        placeholder={open ? 'Search teams' : 'Choose a team'}
        readOnly={!open}
        disabled={disabled}
        data-team-id={value || ''}
        data-testid={testId}
        onClick={() => { if (!open) openPicker() }}
        onChange={(event) => { if (open) setQuery(event.target.value) }}
        onKeyDown={onKeyDown}
      />
      {open && (
        <div className="mt-1 rounded border border-gray-600 bg-gray-900 p-2">
          <button
            type="button"
            className="text-xs underline"
            onClick={() => setAllSeasons((current) => !current)}
            aria-pressed={allSeasons}
          >
            {allSeasons ? 'Search this season only' : 'Search all seasons'}
          </button>
          <ul id={listId} role="listbox" aria-label={`${label} options`} className="mt-1 max-h-60 overflow-auto">
            {results.map((team, index) => (
              <li
                key={team.id}
                id={`${listId}-option-${index}`}
                role="option"
                aria-selected={team.id === value}
                className={`cursor-pointer p-1 ${index === activeIndex ? 'bg-gray-700' : ''}`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(team)}
              >
                {team.name} {team.season}
              </li>
            ))}
            {!results.length && <li className="p-1 text-sm">No teams match that search.</li>}
          </ul>
        </div>
      )}
    </div>
  )
}
