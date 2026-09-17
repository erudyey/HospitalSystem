import "./app.css";
import App from "./App.svelte";
import { mount } from "svelte";

const target = document.getElementById("app");
if (!target) {
  throw new Error("Failed to find app root container.");
}

// In Svelte 5, use mount(App, { target })
const app = mount(App, { target });

export default app;
