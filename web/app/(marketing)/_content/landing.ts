import type { LandingContent } from "../_components/landing/types";

export const landing: LandingContent = {
  hero: {
    eyebrow: "Neurolinguistics",
    headline: "The cognitive science of how language lives in the brain.",
    body: "A self-paced course for curious learners. Create an account to enroll and track your progress across devices.",
  },

  stats: [
    { value: "2,400+", label: "Learners enrolled", placeholder: true },
    { value: "6", label: "Courses in the catalog", placeholder: true },
    { value: "4.8", label: "Average course rating", placeholder: true },
  ],

  courses: [
    {
      slug: "foundations-of-neurolinguistics",
      title: "Foundations of Neurolinguistics",
      description: "Where language sits in the brain, and how we found out.",
      priceCents: 14900,
      rating: 4.9,
      ratingCount: 312,
      placeholder: true,
    },
    {
      slug: "aphasia-and-the-damaged-brain",
      title: "Aphasia and the Damaged Brain",
      description:
        "What losing words after a stroke reveals about how we produce them.",
      priceCents: 12900,
      rating: 4.8,
      ratingCount: 187,
      placeholder: true,
    },
    {
      slug: "the-bilingual-brain",
      title: "The Bilingual Brain",
      description:
        "How two languages share, compete for, and reshape the same neural space.",
      priceCents: 12900,
      rating: 4.7,
      ratingCount: 143,
      placeholder: true,
    },
  ],

  instructor: {
    name: "Dr. Elena Marsh",
    title: "Cognitive neuroscientist and lecturer",
    bio: [
      "Elena has spent fifteen years studying how the brain turns sound into meaning, first in a clinical aphasia lab and then teaching undergraduate cognitive science.",
      "She built this course for the people who kept stopping her after public lectures to ask one more question.",
    ],
    credentials: [
      "PhD, Cognitive Neuroscience",
      "Former lecturer in psycholinguistics",
      "Author of 20+ peer-reviewed papers on language processing",
      "Clinical research fellow, aphasia rehabilitation",
    ],
    placeholder: true,
  },

  testimonials: [
    {
      quote:
        "I have been speaking English for forty years and never once wondered how. Three modules in, I can't stop noticing it.",
      name: "Marcus T.",
      context: "Retired engineer",
      placeholder: true,
    },
    {
      quote: "Dense where it needs to be, and never showing off.",
      name: "Priya R.",
      context: "Speech-language graduate student",
      placeholder: true,
    },
    {
      quote:
        "Finally a course that explains the research instead of just the headlines.",
      name: "Jonas W.",
      context: "High school biology teacher",
      placeholder: true,
    },
  ],

  pricing: [
    {
      name: "Single course",
      summary: "One course, yours to keep.",
      billing: "one-time",
      price: { amountCents: 12900, note: "Lifetime access" },
      features: [
        "Every lesson in the course",
        "Downloadable slides and worksheets",
        "Certificate of completion",
      ],
      cta: { label: "Browse courses", href: "/courses" },
      placeholder: true,
    },
    {
      name: "Bundle",
      summary: "A curated set of related courses at a discount.",
      billing: "one-time",
      price: { amountCents: 32900, note: "Three courses, save 25%" },
      features: [
        "Everything in a single course",
        "Courses sequenced to build on each other",
        "Lifetime access to every course in the bundle",
      ],
      cta: { label: "See bundles", href: "/courses" },
      placeholder: true,
    },
    {
      name: "All-access",
      summary: "Every course, including the ones we haven't published yet.",
      billing: "recurring",
      monthly: { amountCents: 2900, period: "month" },
      annual: {
        amountCents: 24900,
        period: "year",
        note: "Two months free",
      },
      features: [
        "Every published course",
        "New courses as soon as they launch",
        "Cancel anytime; courses you bought outright stay yours",
      ],
      cta: { label: "Start all-access", href: "/sign-up" },
      highlighted: true,
      placeholder: true,
    },
  ],

  lowRisk: {
    line: "Cancel all-access anytime, and if a course isn't for you, ask for a refund within 30 days.",
    placeholder: true,
  },
};
