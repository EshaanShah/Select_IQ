import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("shows the Alpha workflow scaffold", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "SelectIQ Alpha" })).toBeInTheDocument();
    expect(screen.getByText(/US-01\/US-03/)).toBeInTheDocument();
    expect(screen.getByText(/US-10/)).toBeInTheDocument();
  });
});

