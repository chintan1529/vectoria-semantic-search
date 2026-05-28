import { Navbar } from "@/components/layout/navbar";
import { AnimatedBackground } from "@/components/landing/animated-background";
import { HeroSection } from "@/components/landing/hero-section";

export default function Home() {
  return (
    <main className="relative flex min-h-screen flex-col">
      <AnimatedBackground />
      <Navbar />
      <HeroSection />
    </main>
  );
}
