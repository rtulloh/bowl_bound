// Presentation only: labels, roles, observed faces and total all come from the engine.
const colors = {
  black: 'bg-black text-white border-gray-500',
  white: 'bg-white text-black border-gray-600',
  red: 'bg-red-800 text-white border-red-950',
  green: 'bg-green-800 text-white border-green-950',
}
export default function DiceRoll({ roll }) {
  if (!roll) return null
  if (!roll.dice) return <span>{roll.faces.join(' + ')} = {roll.total}</span>
  return (
    <span className="inline-flex flex-wrap items-center gap-2 my-1" role="group" aria-label={roll.dice_label}>
      {roll.dice.map((die) => <span key={die.role} className="inline-flex flex-col items-center gap-1">
        <span className={`inline-flex items-center justify-center w-9 h-9 rounded-md border-2 font-bold text-lg ${colors[die.color] || 'bg-gray-100 text-black'}`}
          role="img" aria-label={`${die.label}: ${die.face}`} data-die-color={die.color}>{die.face}</span>
        <span className="text-xs">{die.label}</span>
      </span>)}
      <span className="font-bold">Total {roll.total}</span>
    </span>
  )
}
