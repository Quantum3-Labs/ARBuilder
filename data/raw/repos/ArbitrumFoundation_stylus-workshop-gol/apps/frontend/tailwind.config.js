/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'navy': '#213147',
        'light-blue': '#12AAFF',
        'moon': '#E5E5E5',
        'white': '#FFFFFF',
        'nova-orange': '#FF7700',
        'shift-blue': '#1B4ADD',
        'stylus-pink': '#FF5F9E',
        'stylus-pink': '#E3066E',
        'black': '#000000',
        'primary': {
          DEFAULT: '#4F46E5',
          '50': '#EEF2FF',
          '100': '#E0E7FF',
          '200': '#C7D2FE',
          '300': '#A5B4FC',
          '400': '#818CF8',
          '500': '#6366F1',
          '600': '#4F46E5',
          '700': '#4338CA',
          '800': '#3730A3',
          '900': '#312E81',
          '950': '#1E1B4B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  variants: {
    extend: {
      backgroundColor: ['responsive', 'hover', 'focus', 'active', 'disabled'],
      textColor: ['responsive', 'hover', 'focus', 'active', 'disabled'],
      borderColor: ['responsive', 'hover', 'focus', 'active', 'disabled'],
      opacity: ['responsive', 'hover', 'focus', 'active', 'disabled'],
      cursor: ['responsive', 'hover', 'focus', 'disabled'],
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
