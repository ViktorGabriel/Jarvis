/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#050811",
          card: "rgba(10, 18, 30, 0.75)",
          border: "rgba(0, 240, 255, 0.25)",
          cyan: "#00f0ff",
          cyanGlow: "rgba(0, 240, 255, 0.5)",
          amber: "#ffb703",
          alert: "#ff3366",
          blue: "#0077b6",
        }
      },
      boxShadow: {
        'hud-cyan': '0 0 20px rgba(0, 240, 255, 0.35)',
        'hud-amber': '0 0 20px rgba(255, 183, 3, 0.4)',
        'hud-alert': '0 0 25px rgba(255, 51, 102, 0.5)',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        hud: ['"Rajdhani"', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
