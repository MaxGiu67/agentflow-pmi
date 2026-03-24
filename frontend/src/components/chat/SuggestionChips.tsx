interface SuggestionChipsProps {
  suggestions: string[]
  onSelect: (message: string) => void
  disabled?: boolean
}

export default function SuggestionChips({ suggestions, onSelect, disabled }: SuggestionChipsProps) {
  if (suggestions.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          onClick={() => onSelect(suggestion)}
          disabled={disabled}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-50"
        >
          {suggestion}
        </button>
      ))}
    </div>
  )
}
