import type { Permission, PermissionLevel } from "./types.js"
import { PERMISSION_LEVELS } from "./types.js"

export class SecurityManager {
  private permissions: Map<string, Set<Permission>> = new Map()

  grant(pluginId: string, permissions: Permission[]): void {
    const current = this.permissions.get(pluginId) ?? new Set()
    for (const p of permissions) {
      current.add(p)
    }
    this.permissions.set(pluginId, current)
  }

  revoke(pluginId: string, permissions?: Permission[]): void {
    if (!permissions) {
      this.permissions.delete(pluginId)
      return
    }
    const current = this.permissions.get(pluginId)
    if (current) {
      for (const p of permissions) {
        current.delete(p)
      }
    }
  }

  getPermissions(pluginId: string): Permission[] {
    return Array.from(this.permissions.get(pluginId) ?? [])
  }

  hasPermission(pluginId: string, permission: Permission): boolean {
    const perms = this.permissions.get(pluginId)
    return perms?.has(permission) ?? false
  }

  getLevel(pluginId: string): PermissionLevel {
    let maxLevel: PermissionLevel = 0
    const perms = this.permissions.get(pluginId) ?? new Set()
    for (const p of perms) {
      const lvl = PERMISSION_LEVELS[p]
      if (lvl !== undefined && lvl > maxLevel) {
        maxLevel = lvl
      }
    }
    return maxLevel
  }

  check(pluginId: string, permission: Permission): void {
    if (!this.hasPermission(pluginId, permission)) {
      throw new Error(`Plugin ${pluginId} missing required permission: ${permission}`)
    }
  }

  filterPermissions(requested: Permission[], allowed: Permission[]): Permission[] {
    return requested.filter((p) => allowed.includes(p))
  }

  validateManifestPermissions(permissions: Permission[]): Permission[] {
    const valid: Permission[] = []
    for (const p of permissions) {
      if (PERMISSION_LEVELS[p] !== undefined) {
        valid.push(p)
      }
    }
    return valid
  }
}

export function createPermissionSet(permissions: Permission[]): Set<Permission> {
  return new Set(permissions)
}

export function mergePermissionSets(...sets: Set<Permission>[]): Set<Permission> {
  const merged = new Set<Permission>()
  for (const s of sets) {
    for (const p of s) {
      merged.add(p)
    }
  }
  return merged
}
