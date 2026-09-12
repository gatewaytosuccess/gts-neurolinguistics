import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";

import { clerkAppearance } from "@/lib/clerk-appearance";
import "./globals.css";

// next/font loads only `wght` unless other axes are named.
const fraunces = Fraunces({
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-fraunces",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-source-sans",
});

export const metadata: Metadata = {
  title: {
    default: "GTS Neurolinguistics",
    template: "%s · GTS Neurolinguistics",
  },
  description:
    "An online course in neurolinguistics — the cognitive science of how language lives in the brain.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <ClerkProvider appearance={clerkAppearance}>
      <html
        lang="en"
        className={`${fraunces.variable} ${sourceSans.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-paper text-accent-strong">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
