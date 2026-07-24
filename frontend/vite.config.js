import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev server on :5173; talks to the FastAPI backend via VITE_API_BASE.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
