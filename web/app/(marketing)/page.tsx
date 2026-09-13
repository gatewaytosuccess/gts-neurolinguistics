import { CoursePreview } from "./_components/landing/course-preview";
import { Hero } from "./_components/landing/hero";
import { InstructorCredentials } from "./_components/landing/instructor-credentials";
import { LowRiskBand } from "./_components/landing/low-risk-band";
import { NewsletterSignup } from "./_components/landing/newsletter-signup";
import { PricingComparison } from "./_components/landing/pricing-comparison";
import { StatBand } from "./_components/landing/stat-band";
import { Testimonials } from "./_components/landing/testimonials";
import { landing } from "./_content/landing";

// The same page for everyone; only the masthead and hero CTAs vary by session.
export default function LandingPage() {
  return (
    <>
      <Hero content={landing.hero} />
      <StatBand stats={landing.stats} />
      <CoursePreview courses={landing.courses} />
      <InstructorCredentials instructor={landing.instructor} />
      <Testimonials testimonials={landing.testimonials} />
      <PricingComparison tiers={landing.pricing} />
      <LowRiskBand content={landing.lowRisk} />
      <NewsletterSignup />
    </>
  );
}
