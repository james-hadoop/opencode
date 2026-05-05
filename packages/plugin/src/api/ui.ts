import type { Permission, DialogOptions, DialogResult } from "../types.js"

export type NotificationType = "info" | "success" | "warning" | "error"

export class UIAPI {
  private permissions: Set<Permission>
  private notifyFn?: (message: string, type: NotificationType) => void
  private dialogFn?: (opts: DialogOptions) => Promise<DialogResult>

  constructor(permissions: Set<Permission>) {
    this.permissions = permissions
  }

  private check(perm: Permission): void {
    if (!this.permissions.has(perm)) {
      throw new Error(`Permission denied: ${perm}`)
    }
  }

  setNotifyFn(fn: (message: string, type: NotificationType) => void): void {
    this.notifyFn = fn
  }

  setDialogFn(fn: (opts: DialogOptions) => Promise<DialogResult>): void {
    this.dialogFn = fn
  }

  showNotification(message: string, type: NotificationType = "info"): void {
    this.check("ui:notification")
    if (this.notifyFn) {
      this.notifyFn(message, type)
    }
  }

  async showDialog(options: DialogOptions): Promise<DialogResult> {
    this.check("ui:dialog")
    if (!this.dialogFn) {
      throw new Error("Dialog function not configured")
    }
    return this.dialogFn(options)
  }

  async renderMarkdown(markdown: string): Promise<void> {
    this.check("ui:render")
  }
}
