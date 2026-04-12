import type { Metadata } from "next";
import { Footer, Layout, Navbar } from "nextra-theme-docs";
import { Head } from "nextra/components";
import { getPageMap } from "nextra/page-map";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "RAG-Forge Docs",
    template: "%s — RAG-Forge",
  },
  description:
    "Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in.",
  metadataBase: new URL("https://rag-forge-docs.vercel.app"),
};

const navbar = (
  <Navbar
    logo={<span style={{ fontFamily: "monospace", fontWeight: 700 }}>[ rag-forge ]</span>}
    projectLink="https://github.com/hallengray/rag-forge"
  />
);

const footer = (
  <Footer>
    <span style={{ fontFamily: "monospace" }}>
      MIT licensed · © {new Date().getFullYear()} Femi Adedayo
    </span>
  </Footer>
);

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <Head
        color={{
          hue: 152,
          saturation: 100,
          lightness: { dark: 50, light: 42 },
        }}
      />
      <body>
        <Layout
          navbar={navbar}
          footer={footer}
          pageMap={await getPageMap()}
          docsRepositoryBase="https://github.com/hallengray/rag-forge/tree/main/apps/docs/content"
          sidebar={{ defaultMenuCollapseLevel: 1 }}
          darkMode
          nextThemes={{ defaultTheme: "dark" }}
        >
          {children}
        </Layout>
      </body>
    </html>
  );
}
