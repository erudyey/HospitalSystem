export type ToastType = "success" | "error" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

class ToastStore {
  toasts = $state<ToastItem[]>([]);

  show(message: string, type: ToastType = "info", durationMs = 3500) {
    const id = Math.random().toString(36).substring(2, 9);
    const item: ToastItem = { id, type, message };
    this.toasts.push(item);

    if (durationMs > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, durationMs);
    }
    return id;
  }

  success(message: string, durationMs = 3500) {
    return this.show(message, "success", durationMs);
  }

  error(message: string, durationMs = 4500) {
    return this.show(message, "error", durationMs);
  }

  info(message: string, durationMs = 3500) {
    return this.show(message, "info", durationMs);
  }

  dismiss(id: string) {
    const idx = this.toasts.findIndex((t) => t.id === id);
    if (idx !== -1) {
      this.toasts.splice(idx, 1);
    }
  }
}

export const toast = new ToastStore();
