import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, duration, Empty, money, percent } from "./ui";

describe("measured results", () => {
  it("does not turn missing measurements into zero", () => {
    expect(percent(undefined)).toBe("—");
    expect(duration(null)).toBe("—");
    expect(money(undefined)).toBe("Not reported");
    expect(percent(0)).toBe("0.0%");
  });
  it("shows inconclusive gate states explicitly", () => {
    render(<Badge value="INCONCLUSIVE" />);
    expect(screen.getByText("INCONCLUSIVE")).toBeInTheDocument();
  });
  it("explains how empty views become useful", () => {
    render(
      <Empty title="No evaluation runs yet">
        Start an evaluation to see results.
      </Empty>,
    );
    expect(screen.getByText("No evaluation runs yet")).toBeInTheDocument();
    expect(
      screen.getByText("Start an evaluation to see results."),
    ).toBeInTheDocument();
  });
});
