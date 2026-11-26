/** 1 → I, 4 → IV, 12 → XII: act numbers, as old books print them. */
export function roman(n: number): string {
  const marks: [number, string][] = [
    [1000, 'M'],
    [900, 'CM'],
    [500, 'D'],
    [400, 'CD'],
    [100, 'C'],
    [90, 'XC'],
    [50, 'L'],
    [40, 'XL'],
    [10, 'X'],
    [9, 'IX'],
    [5, 'V'],
    [4, 'IV'],
    [1, 'I'],
  ]
  let left = Math.max(1, Math.floor(n))
  let text = ''
  for (const [value, mark] of marks) {
    while (left >= value) {
      text += mark
      left -= value
    }
  }
  return text
}
