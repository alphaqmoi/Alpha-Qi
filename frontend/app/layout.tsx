"use client";

import React from "react";
import { ToastProvider } from "@/components/ui/toast-provider";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ToastProvider>{children}</ToastProvider>;
}
