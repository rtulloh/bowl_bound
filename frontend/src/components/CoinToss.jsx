// Coin appearance adapted from Paydirt (MIT, rtulloh); no random outcome or CPU choice.
import PenaltyChoices from './PenaltyChoices'
import DiceRoll from './DiceRoll'

export default function CoinToss({ pending, winner, revealed = true, rolls = [], onChoose, disabled }) {
  return (
    <section className="board-panel p-4 text-center" data-testid="coin-toss" aria-label="Opening toss">
      <h2 className="text-xl font-bold mb-3">Opening toss</h2>
      <div className={`${revealed ? "" : "toss-coin "}w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center shadow-xl`} aria-hidden="true" data-testid="coin">
        <span className="text-4xl font-bold text-yellow-900">{revealed ? "BB" : "?"}</span>
      </div>
      {!revealed ? <p className="my-3" role="status" data-testid="toss-flipping">Flipping coin…</p> : <>
      <p className="my-3">{winner || pending?.chooser} won the engine toss.</p>
      {pending && <PenaltyChoices pending={pending} onChoose={onChoose} disabled={disabled} />}
      <details className="mt-3 text-sm text-left">
        <summary className="cursor-pointer">Toss dice audit</summary>
        <p className="my-2">The coin presents the result; the recorded Bowl Bound dice determine the winner.</p>
        <div className="flex flex-wrap justify-center gap-3">{rolls.map((roll, i) => <DiceRoll key={i} roll={roll} />)}</div>
      </details>
      </>}
    </section>
  )
}
