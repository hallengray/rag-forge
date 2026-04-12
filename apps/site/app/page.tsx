import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { TrustBadges } from "@/components/trust-badges";
import { ProblemSection } from "@/components/problem-section";
import { FeatureGrid } from "@/components/feature-grid";
import { RmmLadder } from "@/components/rmm-ladder";
import { QuickStart } from "@/components/quick-start";
import { ComparisonTable } from "@/components/comparison-table";
import { Templates } from "@/components/templates";
import { Footer } from "@/components/footer";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <TrustBadges />
        <ProblemSection />
        <FeatureGrid />
        <RmmLadder />
        <QuickStart />
        <ComparisonTable />
        <Templates />
      </main>
      <Footer />
    </>
  );
}
