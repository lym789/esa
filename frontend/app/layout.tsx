import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "企业支持智能体",
  description: "面向企业知识库与智能工单的智能体工作台"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
