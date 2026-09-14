// Hex values duplicate the tokens in globals.css; keep them in sync.
export const clerkAppearance = {
  variables: {
    colorPrimary: "#db9e38",
    // White on this gold is only 2.3:1.
    colorPrimaryForeground: "#261e0f",
    colorForeground: "#261e0f",
    colorMutedForeground: "#4a5a68",
    colorBackground: "#fcfaf6",
    colorInput: "#fcfaf6",
    colorInputForeground: "#261e0f",
    colorBorder: "#857f74",
    colorRing: "#0a2463",
    colorDanger: "#a12f2f",
    colorSuccess: "#225a31",
    colorWarning: "#6e4200",
    fontFamily:
      'var(--font-source-sans), -apple-system, "Segoe UI", Helvetica, Arial, sans-serif',
    borderRadius: "6px",
  },
  options: {
    logoPlacement: "none" as const,
  },
  elements: {
    cardBox: {
      // Shadows are reserved for dropdowns, modals and tooltips.
      boxShadow: "none",
      border: "1px solid #c1bdb5",
      borderRadius: "10px",
    },
    card: {
      backgroundColor: "#fcfaf6",
    },
    headerTitle: {
      fontFamily: 'var(--font-fraunces), "Source Serif 4", Georgia, serif',
      fontSize: "30px",
      fontWeight: 600,
      letterSpacing: "-0.015em",
      fontVariationSettings: '"wght" 600, "SOFT" 30, "WONK" 0, "opsz" 30',
    },
    formButtonPrimary: {
      borderRadius: "6px",
      fontSize: "16px",
      fontWeight: 600,
      textTransform: "none",
      "&:hover": {
        backgroundColor: "#925100",
        color: "#fcfaf6",
      },
    },
    input: {
      borderRadius: "4px",
    },
    socialButtonsBlockButton: {
      borderRadius: "6px",
      borderColor: "#857f74",
    },
    footerActionLink: {
      color: "#925100",
    },
  },
};
