import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  publicDir: "../src/emojibench/data",
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
