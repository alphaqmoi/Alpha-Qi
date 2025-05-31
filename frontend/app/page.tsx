"use client";

import "./index.css";
import App from "./App";
import { ThemeProvider } from "@/components/ui/theme-provider";

export default function Page() {
  return (
    <ThemeProvider defaultTheme="dark">
      <App />
    </ThemeProvider>
  );
}
