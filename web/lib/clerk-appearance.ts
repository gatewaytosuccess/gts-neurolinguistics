/*
 * DESIGN.md, expressed in Clerk's appearance vocabulary.
 *
 * Clerk's prebuilt <SignUp /> and <SignIn /> cards render inside our own page
 * chrome, so they have to speak the same visual language as everything around
 * them. Most of that lands through `variables`; `elements` covers the handful
 * of things the variable set cannot say -- notably that the card must not
 * carry a shadow (DESIGN.md gives shadows only to dropdowns, modals and
 * tooltips) and that the primary button is Brass Seal with dark ink on it,
 * never white, which fails contrast badly against a mid-lightness gold.
 */
export const clerkAppearance = {
  variables: {
    colorPrimary: "#db9e38",
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
    fontFamily: 'var(--font-source-sans), -apple-system, "Segoe UI", Helvetica, Arial, sans-serif',
    borderRadius: "6px",
  },
  options: {
    logoPlacement: "none" as const,
  },
  elements: {
    cardBox: {
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
