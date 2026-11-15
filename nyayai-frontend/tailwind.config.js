export default {
  content: ["./index.html","./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        forest: { 50:"#F0F7F4", 100:"#D9EDE5", 200:"#B3DBCB", 300:"#7DC0A6", 400:"#4DA382", 500:"#2D7A5F", 600:"#1B5C45", 700:"#154736", 800:"#0E3026", 900:"#091C17" },
        gold:   { 50:"#FFFBEB", 100:"#FEF3C7", 400:"#FBBF24", 500:"#D4A017", 600:"#B7860E", 700:"#9A6C07" },
        stone:  { 50:"#FAFAF8", 100:"#F5F5F0", 200:"#EAEAE3", 300:"#D6D6CC", 400:"#A8A89A", 500:"#737368", 600:"#525248", 700:"#3A3A33", 900:"#1A1A14" },
      },
      fontFamily: {
        display: ["'Cormorant Garamond'","Georgia","serif"],
        body:    ["'DM Sans'","system-ui","sans-serif"],
      },
      boxShadow: {
        card:  "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        lift:  "0 4px 16px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04)",
        modal: "0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08)",
      },
      keyframes: {
        "fade-up":  { "0%":{ opacity:"0", transform:"translateY(16px)" }, "100%":{ opacity:"1", transform:"translateY(0)" } },
        "fade-in":  { "0%":{ opacity:"0" }, "100%":{ opacity:"1" } },
        dot:        { "0%,80%,100%":{ opacity:"0.3", transform:"scale(0.8)" }, "40%":{ opacity:"1", transform:"scale(1)" } },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16,1,0.3,1) forwards",
        "fade-in": "fade-in 0.4s ease forwards",
        dot:       "dot 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
