import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const displayFont = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
});

const textFont = Manrope({
  variable: "--font-text",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Fund Nav | Online Estimation Dashboard",
  description: "Track real-time fund NAV estimation and watchlists.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${displayFont.variable} ${textFont.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
