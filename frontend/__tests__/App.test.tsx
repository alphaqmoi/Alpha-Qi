// __tests__/App.test.tsx

import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import App from "../pages/index"; // adjust if App is elsewhere

describe("App", () => {
  it("renders the app component", () => {
    render(<App />);
    expect(screen.getByText(/welcome/i)).toBeInTheDocument(); // adjust text
  });
});
