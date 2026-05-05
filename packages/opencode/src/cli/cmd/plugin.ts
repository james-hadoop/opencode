import type { Argv } from "yargs"
import { cmd } from "./cmd"
import { UI } from "../ui"
import { Config } from "../../config/config"
import * as fs from "fs/promises"
import * as path from "path"

export const PluginCommand = cmd({
  command: "plugin <action> [plugin]",
  describe: "manage plugins",
  builder: (yargs: Argv) => {
    return yargs
      .positional("action", {
        describe: "action to perform",
        type: "string",
        choices: ["list", "install", "uninstall", "enable", "disable"],
        demandOption: true,
      })
      .positional("plugin", {
        describe: "plugin name or path",
        type: "string",
      })
      .option("global", {
        describe: "install globally",
        type: "boolean",
      })
  },
  handler: async (args) => {
    const action = args.action
    const pluginArg = args.plugin as string | undefined

    switch (action) {
      case "list":
        await listPlugins()
        break
      case "install":
        if (!pluginArg) {
          UI.error("Plugin name or path required")
          return
        }
        await installPlugin(pluginArg, args.global)
        break
      case "uninstall":
        if (!pluginArg) {
          UI.error("Plugin name required")
          return
        }
        await uninstallPlugin(pluginArg)
        break
      case "enable":
        if (!pluginArg) {
          UI.error("Plugin name required")
          return
        }
        await enablePlugin(pluginArg)
        break
      case "disable":
        if (!pluginArg) {
          UI.error("Plugin name required")
          return
        }
        await disablePlugin(pluginArg)
        break
    }
  },
})

async function listPlugins() {
  const cfg = await Config.get()
  const plugins = cfg.plugin ?? []

  if (plugins.length === 0) {
    UI.println("No plugins installed")
    return
  }

  UI.println(UI.Style.TEXT_SUCCESS_BOLD + "Installed plugins:" + UI.Style.TEXT_NORMAL)
  for (const p of plugins) {
    UI.println(`  - ${p}`)
  }
}

async function installPlugin(source: string, global?: boolean) {
  UI.println(`Installing plugin: ${source}`)

  const cfg = await Config.get()
  const plugins = cfg.plugin ?? []

  if (plugins.includes(source)) {
    UI.error(`Plugin already installed: ${source}`)
    return
  }

  plugins.push(source)
  await Config.update({ plugin: plugins })

  UI.println(UI.Style.TEXT_SUCCESS_BOLD + "Plugin installed successfully" + UI.Style.TEXT_NORMAL)
}

async function uninstallPlugin(name: string) {
  UI.println(`Uninstalling plugin: ${name}`)

  const cfg = await Config.get()
  let plugins = cfg.plugin ?? []

  const filtered = plugins.filter((p) => !p.includes(name))
  if (filtered.length === plugins.length) {
    UI.error(`Plugin not found: ${name}`)
    return
  }

  await Config.update({ plugin: filtered })

  UI.println(UI.Style.TEXT_SUCCESS_BOLD + "Plugin uninstalled successfully" + UI.Style.TEXT_NORMAL)
}

async function enablePlugin(name: string) {
  UI.println(`Enabling plugin: ${name}`)
  UI.println(UI.Style.TEXT_WARNING + "Note: Plugin enable/disable not yet implemented" + UI.Style.TEXT_NORMAL)
}

async function disablePlugin(name: string) {
  UI.println(`Disabling plugin: ${name}`)
  UI.println(UI.Style.TEXT_WARNING + "Note: Plugin enable/disable not yet implemented" + UI.Style.TEXT_NORMAL)
}
