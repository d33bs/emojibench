import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("offline kitchen", () => {
  it("filters concepts, fills both slots, and renders a preview", () => {
    render(<App />);

    const search = screen.getByRole("searchbox", { name: "Search concepts" });
    fireEvent.change(search, { target: { value: "macrophage" } });
    expect(screen.getByRole("button", { name: "Select Macrophage" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Select Superhero" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Select Macrophage" }));
    expect(screen.getByTestId("selection-one")).toHaveTextContent("Macrophage");

    fireEvent.change(search, { target: { value: "hero" } });
    fireEvent.click(screen.getByRole("button", { name: "Select Superhero" }));

    expect(screen.getByTestId("selection-two")).toHaveTextContent("Superhero");
    expect(screen.getByTestId("combination-preview")).toBeVisible();
    expect(screen.getByText("Mock offline preview")).toBeVisible();
    expect(screen.getByRole("button", { name: "Download SVG" })).toBeEnabled();
  });

  it("shows the offline note when the backend is unavailable", async () => {
    render(<App />);

    const notes = await screen.findAllByTestId("backend-note");
    expect(notes.length).toBeGreaterThan(0);
    expect(notes[0]).toHaveTextContent("offline demo");
  });
});
