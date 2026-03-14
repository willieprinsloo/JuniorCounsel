import type { Metadata } from "next";
import { Inter, EB_Garamond } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/context";
import { ThemeProvider } from "@/lib/theme/context";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: 'swap',
});

const ebGaramond = EB_Garamond({
  variable: "--font-eb-garamond",
  subsets: ["latin"],
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Junior Counsel",
  description: "AI-powered legal document drafting for South African litigation",
  icons: {
    icon: '/Junior-Counsel-Favicon.svg',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preload" as="image" href="/logo-no-text.svg" />
      </head>
      <body
        className={`${inter.variable} ${ebGaramond.variable} font-sans antialiased`}
        style={{ fontFamily: 'Inter, sans-serif' }}
      >
        <ThemeProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
