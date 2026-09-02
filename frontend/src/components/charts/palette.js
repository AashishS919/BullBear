/**
 * Hex equivalents of the oklch design tokens, for charting libraries that
 * render SVG fills more reliably with hex than with oklch() strings.
 * Keep these in sync with the @theme tokens in src/index.css.
 *   bull  oklch(0.62 0.17 145)
 *   bear  oklch(0.62 0.17 25)
 *   accent oklch(0.62 0.17 250)
 */
export const CHART = {
  bull: '#1c9d57',
  bear: '#d6463c',
  accent: '#3c7ae4',
  ink: '#0E1116',
  ink3: '#6B7178',
  line: '#E7E5DE',
  paper: '#FAFAF7',
  surface: '#FFFFFF',
}
