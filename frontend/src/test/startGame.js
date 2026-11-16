import { screen, waitFor } from '@testing-library/react'

/**
 * Wait until the setup screen can actually start a game.
 *
 * Start stays disabled until the matching rules summary resolves, so tests
 * must wait for readiness rather than only for the button to exist.
 */
export async function waitForStartReady() {
  const button = await screen.findByTestId('start-game')
  await waitFor(() => expect(button).toBeEnabled())
  return button
}
