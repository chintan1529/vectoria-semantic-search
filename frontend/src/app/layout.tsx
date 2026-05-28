import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CommandPalette } from "@/components/ui/command-palette";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Vectoria — Neural Retrieval & Grounded Generation",
  description:
    "Production-grade semantic search and retrieval-augmented generation engine. " +
    "Powered by all-MiniLM-L6-v2, FAISS IndexFlatIP, and cross-encoder reranking.",
  keywords: [
    "semantic search",
    "RAG",
    "retrieval augmented generation",
    "FAISS",
    "neural retrieval",
    "vector search",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-[#09090b] text-zinc-50 selection:bg-v-blue/30 selection:text-white" suppressHydrationWarning>
        <CommandPalette />
        {children}
      </body>
    </html>
  );
}
