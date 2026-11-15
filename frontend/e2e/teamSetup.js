// The setup screen scopes each side's team list to its selected season, so a
// test must choose the year before the team. Team IDs are season/team-slug.
//
// Small catalogs render a native select; large catalogs render a searchable
// combobox. Support both so tests do not depend on catalog size.
export async function selectTeam(page, side, teamId) {
  const [season, slug] = teamId.split('/')
  await page.getByTestId(`${side}-season`).selectOption(season)
  const control = page.getByTestId(`${side}-select`)
  if ((await control.evaluate((element) => element.tagName)) === 'SELECT') {
    await control.selectOption(teamId)
    return
  }
  await control.click()
  await control.fill(slug)
  await page.getByRole('listbox').getByRole('option', { name: new RegExp(`${season}`, 'i') }).first().click()
}

export async function selectTeams(page, home, away) {
  await selectTeam(page, 'home', home)
  await selectTeam(page, 'away', away)
}

// Return the canonical team ID for both control types so assertions stay exact.
export async function selectedTeam(page, side) {
  const control = page.getByTestId(`${side}-select`)
  if ((await control.evaluate((element) => element.tagName)) === 'SELECT') {
    return control.inputValue()
  }
  return control.getAttribute('data-team-id')
}
