import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAG-Forge — Production-grade RAG pipelines with evaluation baked in",
  description:
    "Framework-agnostic CLI toolkit that scaffolds production-grade RAG pipelines with evaluation baked in from day one. Score any RAG system against the RAG Maturity Model.",
  keywords: [
    "rag",
    "retrieval-augmented-generation",
    "evaluation",
    "llm",
    "rag-pipeline",
    "ragas",
  ],
  authors: [{ name: "Femi Adedayo" }],
  openGraph: {
    title: "RAG-Forge",
    description:
      "Production-grade RAG pipelines with evaluation baked in. Scaffold, evaluate, and assess any pipeline against the RAG Maturity Model.",
    url: "https://rag-forge.vercel.app",
    siteName: "RAG-Forge",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
