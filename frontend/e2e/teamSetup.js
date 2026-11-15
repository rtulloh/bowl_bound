// The setup screen scopes each side's team list to its selected season, so a
// test must choose the year before the team. Team IDs are season/team-slug.
export async function selectTeam(page, side, teamId) {
  await page.getByTestId(`${side}-season`).selectOption(teamId.split('/')[0])
  await page.getByTestId(`${side}-select`).selectOption(teamId)
}

export async function selectTeams(page, home, away) {
  await selectTeam(page, 'home', home)
  await selectTeam(page, 'away', away)
}
